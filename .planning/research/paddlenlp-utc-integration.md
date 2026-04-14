# Research: PaddleNLP UTC Model Integration for feedship

**Project:** feedship - Personal News Information System
**Research Date:** 2026-04-11
**Confidence:** MEDIUM-LOW (WebSearch unavailable, based on training knowledge and PyPI package inspection)

---

## Executive Summary

PaddleNLP UTC (Unified Target Classification) is a multi-label zero-shot classification model from Baidu's PaddlePaddle ecosystem. Integration with feedship's evaluate chain is **feasible but comes with significant trade-offs**. The model requires ~3-4GB disk space, CPU inference is slow (2-5 seconds per classification), and GPU acceleration via PaddlePaddle GPU is strongly recommended. The primary benefit would be removing LLM API dependency for the evaluation task, but accuracy on subjective quality evaluation tasks is likely lower than LLM-based evaluation.

---

## 1. UTC Model Overview

### 1.1 What is PaddleNLP UTC?

UTC (Unified Target Classification) is a Baidu-developed model based on the UMT (Unified Multi-label Text Classification) framework. It uses a prompt-based approach for zero-shot and few-shot text classification.

**Architecture:**
- Based on ERNIE (Enhanced Representation through Knowledge Integration) or similar transformer backbone
- Uses prompt templates for multi-label classification
- Supports multi-label and binary classification modes

**Key Characteristics:**
- Designed for Chinese NLP tasks primarily
- Zero-shot capability via prompt engineering
- Multi-label classification (single input can have multiple labels)

### 1.2 Available Model Sizes

| Model | Size | Description |
|-------|------|-------------|
| `utc-base` | ~400MB | Base model (HF PaddlePaddle/utc-base) |
| `utc-large` | ~1-2GB | Larger model with better accuracy |

**Note:** Model sizes are approximate. The `utc-base` variant is most commonly used for deployment. The full PaddlePaddle framework adds additional overhead.

### 1.3 Zero-Shot Classification with UTC

UTC uses prompt-based classification. Labels are defined as natural language descriptions:

```python
labels = ["coherence:高", "coherence:中", "coherence:低"]
result = model.predict(text, labels=labels)
```

The model fills in the prompt template and returns classification results.

### 1.4 Chinese/English Support

- **Primary:** Chinese text classification
- **Secondary:** English support exists but quality may be lower
- For feedship's Chinese news reports, this is well-suited

---

## 2. Integration Feasibility

### 2.1 Installation

```bash
# CPU version
pip install paddlepaddle paddlenlp

# GPU version (requires CUDA 11.7+ or 12.x)
pip install paddlepaddle-gpu paddlenlp
```

**Dependencies:**
- `paddlepaddle`: Core PaddlePaddle framework (~100-200MB)
- `paddlenlp`: NLP library with UTC model (~50MB)

**Total installation footprint:** ~500MB-2GB depending on GPU support

### 2.2 Model Download and Loading

```python
from paddlenlp.transformers import UTC

# First call downloads model (~400MB for utc-base)
model = UTC("PaddlePaddle/utc-base")

# Model loading time: 10-30 seconds (cold start)
```

**Model size on disk:** ~400MB-1GB depending on variant

**Memory footprint:**
- CPU: ~2-3GB RAM during inference
- GPU: ~1-2GB VRAM + 1GB RAM

### 2.3 Inference Latency

| Hardware | Latency per classification | Notes |
|----------|----------------------------|-------|
| CPU (modern) | 2-5 seconds | Single classification |
| GPU (T4/moderate) | 0.2-0.5 seconds | With GPU support |
| GPU (high-end) | 0.1-0.2 seconds | A100/V100 |

**Batch prediction support:** Yes, `model.predict(texts, labels=labels)` accepts lists.

### 2.4 Batch Prediction

```python
# Batch prediction supported
texts = [text1, text2, text3]
results = model.predict(texts, labels=labels)
# Returns list of classification results
```

---

## 3. Label System Design for evaluate chain

### 3.1 Mapping 4 Dimensions to UTC Labels

Current evaluate chain outputs: coherence, relevance, depth, structure (each 0.0-1.0)

**Option A: 3-Level Classification per Dimension (Recommended)**

```python
labels = [
    # Coherence
    "coherence:high", "coherence:medium", "coherence:low",
    # Relevance
    "relevance:high", "relevance:medium", "relevance:low",
    # Depth
    "depth:high", "depth:medium", "depth:low",
    # Structure
    "structure:high", "structure:medium", "structure:low",
]

# Map to scores:
label_to_score = {
    "coherence:high": 1.0,
    "coherence:medium": 0.6,
    "coherence:low": 0.2,
    # ...
}
```

**Option B: Binary Classification per Dimension**

```python
labels = [
    "coherence_good", "coherence_poor",
    "relevance_good", "relevance_poor",
    # ...
]
# Scores: good=1.0, poor=0.3
```

### 3.2 Binary vs 3-Level: Recommendation

**3-level classification is recommended because:**
1. More granular feedback distinguishes medium from high
2. UTC performs better with clear descriptive labels
3. Maps more naturally to 0.0-1.0 score range

### 3.3 Output Format

```python
# UTC predict() returns:
{
    "predictions": [
        {
            "labels": ["coherence:high", "relevance:medium"],
            "scores": [0.92, 0.78]
        }
    ]
}

# Or in multi-label mode, returns all label probabilities
```

### 3.4 Post-Processing: Label to 0.0-1.0 Score

```python
def utc_to_quality_score(utc_result: dict) -> QualityScore:
    """Convert UTC result to QualityScore dataclass."""
    predictions = utc_result["predictions"][0]
    labels = predictions["labels"]
    scores = predictions["scores"]

    label_score_map = {
        "coherence:high": 1.0, "coherence:medium": 0.6, "coherence:low": 0.2,
        "relevance:high": 1.0, "relevance:medium": 0.6, "relevance:low": 0.2,
        "depth:high": 1.0, "depth:medium": 0.6, "depth:low": 0.2,
        "structure:high": 1.0, "structure:medium": 0.6, "structure:low": 0.2,
    }

    # Extract score for each dimension
    coherence = next((label_score_map[l] for l in labels if l.startswith("coherence:")), 0.5)
    relevance = next((label_score_map[l] for l in labels if l.startswith("relevance:")), 0.5)
    depth = next((label_score_map[l] for l in labels if l.startswith("depth:")), 0.5)
    structure = next((label_score_map[l] for l in labels if l.startswith("structure:")), 0.5)

    return QualityScore(
        overall=(coherence + relevance + depth + structure) / 4,
        coherence=coherence,
        relevance=relevance,
        depth=depth,
        structure=structure,
    )
```

---

## 4. Code Integration Plan

### 4.1 Example Integration Code

```python
# src/llm/utc_evaluator.py
"""UTC-based evaluation chain for report quality assessment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from paddlenlp.transformers import UTC

from src.llm.evaluator import QualityScore

logger = logging.getLogger(__name__)

# UTC label definitions for 4-dimension evaluation
UTC_LABELS = [
    # Coherence
    "coherence:high", "coherence:medium", "coherence:low",
    # Relevance
    "relevance:high", "relevance:medium", "relevance:low",
    # Depth
    "depth:high", "depth:medium", "depth:low",
    # Structure
    "structure:high", "structure:medium", "structure:low",
]

# Mapping from UTC labels to 0.0-1.0 scores
LABEL_TO_SCORE = {
    "coherence:high": 1.0, "coherence:medium": 0.6, "coherence:low": 0.2,
    "relevance:high": 1.0, "relevance:medium": 0.6, "relevance:low": 0.2,
    "depth:high": 1.0, "depth:medium": 0.6, "depth:low": 0.2,
    "structure:high": 1.0, "structure:medium": 0.6, "structure:low": 0.2,
}

# Singleton UTC model instance
_utc_model: UTC | None = None


def get_utc_model() -> UTC:
    """Get or initialize the UTC model singleton."""
    global _utc_model
    if _utc_model is None:
        _utc_model = UTC("PaddlePaddle/utc-base")
    return _utc_model


def _label_to_score(label: str) -> float:
    """Convert UTC label to numeric score."""
    return LABEL_TO_SCORE.get(label, 0.5)


async def evaluate_with_utc(report_text: str) -> QualityScore:
    """Evaluate report quality using UTC model.

    Args:
        report_text: The report text to evaluate (first 2000 chars used)

    Returns:
        QualityScore with coherence, relevance, depth, structure scores

    Raises:
        RuntimeError: If UTC model fails to load or predict
    """
    try:
        model = get_utc_model()
        text_input = report_text[:2000]

        # UTC predict returns dict with predictions
        result = model.predict(text_input, labels=UTC_LABELS)

        # Extract predictions
        predictions = result["predictions"][0]
        labels = predictions["labels"]
        scores = predictions["scores"]

        # Map labels to QualityScore dimensions
        coherence = _label_to_score(next((l for l in labels if l.startswith("coherence:")), "coherence:medium"))
        relevance = _label_to_score(next((l for l in labels if l.startswith("relevance:")), "relevance:medium"))
        depth = _label_to_score(next((l for l in labels if l.startswith("depth:")), "depth:medium"))
        structure = _label_to_score(next((l for l in labels if l.startswith("structure:")), "structure:medium"))

        return QualityScore(
            overall=(coherence + relevance + depth + structure) / 4,
            coherence=coherence,
            relevance=relevance,
            depth=depth,
            structure=structure,
        )

    except Exception as e:
        logger.warning("UTC evaluation failed: %s", e)
        raise RuntimeError(f"UTC evaluation failed: {e}") from e


def evaluate_with_utc_fallback(report_text: str) -> QualityScore:
    """Synchronous wrapper with fallback to LLM chain on failure."""
    try:
        return evaluate_with_utc(report_text)
    except RuntimeError:
        logger.info("Falling back to LLM-based evaluation")
        # Fall back to existing LLM chain
        import asyncio
        from src.llm.evaluator import evaluate_report
        return asyncio.run(evaluate_report(report_text))
```

### 4.2 Integration into Current Pipeline

Modify `src/llm/evaluator.py` to add UTC as primary with LLM fallback:

```python
# In src/llm/evaluator.py

# Configuration flag
USE_UTC_EVALUATOR = os.environ.get("FEEDSHIP_USE_UTC", "false").lower() == "true"

async def evaluate_report(report_text: str) -> QualityScore:
    """Use UTC or LLM to evaluate report quality.

    Returns QualityScore with subscores for coherence, relevance, depth, structure.
    """
    if USE_UTC_EVALUATOR:
        try:
            return await evaluate_with_utc(report_text)
        except RuntimeError:
            logger.warning("UTC evaluation failed, falling back to LLM chain")
            # Fall through to LLM chain

    # Original LLM chain code...
    from src.llm.chains import get_evaluate_chain
    chain = get_evaluate_chain()
    # ... rest of existing code
```

### 4.3 Fallback Strategy

```python
# src/llm/utc_evaluator.py additions

def is_utc_available() -> bool:
    """Check if UTC model is available and functional."""
    try:
        model = get_utc_model()
        # Quick health check
        model.predict("test", labels=["coherence:high"])
        return True
    except Exception:
        return False
```

---

## 5. Accuracy Trade-offs

### 5.1 UTC Zero-Shot Accuracy on Subjective Classification

**Known strengths:**
- Factual classification tasks (sentiment, topic)
- Multi-label classification with clear label boundaries
- Chinese text classification (primary use case)

**Known weaknesses for quality evaluation:**
- Subjective judgment tasks (coherence, depth) are harder to classify
- Requires well-crafted prompts for nuanced quality assessment
- May struggle with distinguishing "medium" vs "high" quality

### 5.2 Comparison with LLM-Based Evaluation

| Aspect | UTC | LLM (MiniMax/GPT) |
|--------|-----|-------------------|
| Speed | 0.2-5s (GPU-CPU) | 1-3s API call |
| Cost | One-time compute | Per-call API cost |
| Accuracy (subjective) | Lower | Higher |
| Consistency | Good | Variable |
| Explanation | No | Can provide reasoning |

**Estimate:** UTC zero-shot on quality evaluation is likely 10-20% less accurate than LLM-based evaluation, particularly for nuanced cases.

### 5.3 Known Failure Modes

1. **Label confusion:** UTC may pick multiple labels from same dimension (e.g., both "coherence:high" and "coherence:medium")
2. **Prompt sensitivity:** Results vary with label phrasing
3. **Length sensitivity:** Very long reports may get lower coherence scores
4. **Boundary cases:** Reports at threshold quality levels may be misclassified

---

## 6. Deployment Considerations

### 6.1 Cold Start Time

| Component | Time |
|-----------|------|
| Model download (first run) | 30-60s |
| Model loading (subsequent) | 10-30s |
| First inference | 5-15s (CPU), 1-3s (GPU) |

**Recommendation:** Load model at application startup, keep in memory.

### 6.2 Memory Footprint

| Configuration | RAM | VRAM |
|---------------|-----|------|
| CPU only | 2-4GB | N/A |
| GPU (PaddlePaddle GPU) | 1-2GB | 1-2GB |
| With other ML libs | 3-5GB | 2-4GB |

### 6.3 GPU Requirement

**PaddlePaddle GPU Support:**
- Requires NVIDIA GPU with CUDA 11.7+ or 12.x
- `paddlepaddle-gpu` package needed
- cuDNN and cuBLAS required

**For feedship (CLI tool):**
- CPU-only deployment is possible but slow
- GPU is strongly recommended for production use

### 6.4 Docker/Containerization

```dockerfile
# For CPU-based UTC
FROM python:3.11-slim
RUN pip install paddlepaddle paddlenlp
# Model downloaded at runtime

# For GPU-based UTC
FROM nvidia/cuda:11.7-cudnn8-runtime-ubuntu22.04
RUN pip install paddlepaddle-gpu paddlenlp
```

**Image size impact:** +1-2GB for PaddlePaddle dependencies

### 6.5 Environment Requirements

```bash
# CPU
pip install paddlepaddle paddlenlp

# GPU (CUDA 11.7)
pip install paddlepaddle-gpu==2.6.0 -i https://mirror.baidu.com/pypi/simple

# GPU (CUDA 12.x)
pip install paddlepaddle-gpu==3.0.0b1 -i https://mirror.baidu.com/pypi/simple
```

---

## 7. Recommendations

### 7.1 When to Use UTC

**Use UTC if:**
- API cost is a significant concern
- Offline operation is required
- Evaluation throughput is high (many reports)
- GPU resources are available

**Do NOT use UTC if:**
- Maximum accuracy is required
- Only CPU available and speed matters
- Label calibration effort cannot be invested

### 7.2 Implementation Roadmap

1. **Phase 1:** Add UTC as optional evaluator (behind flag)
   - Implement `src/llm/utc_evaluator.py`
   - Add `USE_UTC` config flag
   - Test on sample reports

2. **Phase 2:** Calibration and validation
   - Compare UTC vs LLM scores on 100+ reports
   - Tune label mappings if needed
   - Validate accuracy

3. **Phase 3:** Production rollout
   - Set `USE_UTC=true` as default if accuracy is acceptable
   - Document fallback behavior
   - Monitor error rates

### 7.3 Label Refinement

Initial labels may need tuning. Start with binary classification:
```python
labels = [
    "report_coherence_good", "report_coherence_poor",
    "report_relevance_good", "report_relevance_poor",
    "report_depth_good", "report_depth_poor",
    "report_structure_good", "report_structure_poor",
]
```

Then expand to 3-level if accuracy is acceptable.

---

## 8. Sources and References

**Note:** WebSearch was unavailable during this research. The following is based on training data and package inspection:

- **PyPI Package:** paddlenlp 2.8.1 (latest stable)
- **GitHub:** https://github.com/PaddlePaddle/PaddleNLP
- **Model Hub:** PaddlePaddle/utc-base on HuggingFace

**Confidence: MEDIUM-LOW**

The technical details about UTC model behavior, accuracy characteristics, and inference performance are based on general knowledge of the PaddleNLP library. Actual performance may vary. Verification against official documentation is recommended before implementation.

---

## 9. Gaps and Follow-ups

1. **Verify model size** - Actual download size for `utc-base` variant
2. **Confirm API** - Exact return format of `model.predict()`
3. **Benchmark** - Real inference speed on representative hardware
4. **Accuracy study** - Compare against LLM evaluation on feedship reports
5. **Label calibration** - Test different label phrasings for quality dimensions
