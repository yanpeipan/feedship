"""Tests for search result ranking logic."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestRankSemanticResults:
    """Tests for rank_semantic_results() function."""

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_basic_ranking_by_similarity(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 1: Basic ranking with similarity only.

        3 results with same source (example.com) and same pub_date (today),
        different distances. Expect results sorted by norm_similarity descending.
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup - returns list of dicts
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
            {"id": "id2", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
            {"id": "id3", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
        ]

        # Mock batch feed lookup - returns dict mapping id -> Feed
        mock_feed = MagicMock()
        mock_feed.weight = None
        mock_get_feeds_by_ids.return_value = {"feed1": mock_feed}

        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "Article 1", "url": "https://blog.example.com/a1", "distance": 0.5, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "Article 2", "url": "https://blog.example.com/a2", "distance": 0.2, "document": "doc2"},
            {"article_id": "a3", "sqlite_id": "id3", "title": "Article 3", "url": "https://blog.example.com/a3", "distance": 0.8, "document": "doc3"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        # Should have all 3 results
        assert len(ranked) == 3
        # Article with smallest distance (highest similarity) should be first
        # distance 0.2 -> cos_sim = 1 - 0.04/2 = 0.98
        # distance 0.5 -> cos_sim = 1 - 0.25/2 = 0.875
        # distance 0.8 -> cos_sim = 1 - 0.64/2 = 0.68
        assert ranked[0]["article_id"] == "a2"  # Best similarity
        assert ranked[1]["article_id"] == "a1"
        assert ranked[2]["article_id"] == "a3"  # Worst similarity

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_freshness_factor(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 2: Freshness factor.

        2 results with same similarity, different pub_dates (1 day ago vs 31 days ago).
        Expect newer article ranked higher (higher freshness score).
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)
        # Article 1: 1 day ago -> freshness = 1 - 1/30 = 0.967
        # Article 2: 31 days ago -> freshness = max(0, 1 - 31/30) = 0
        pub_date_1_day_ago = (now - timedelta(days=1)).isoformat()
        pub_date_31_days_ago = (now - timedelta(days=31)).isoformat()

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": pub_date_1_day_ago, "feed_id": "feed1", "feed_name": "Test Feed"},
            {"id": "id2", "pub_date": pub_date_31_days_ago, "feed_id": "feed1", "feed_name": "Test Feed"},
        ]

        mock_feed = MagicMock()
        mock_feed.weight = None
        mock_get_feeds_by_ids.return_value = {"feed1": mock_feed}

        # Same distance (same similarity) for both
        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "Recent Article", "url": "https://example.com/recent", "distance": 0.5, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "Old Article", "url": "https://example.com/old", "distance": 0.5, "document": "doc2"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 2
        # Recent article should be ranked first (higher freshness)
        assert ranked[0]["article_id"] == "a1"
        assert ranked[1]["article_id"] == "a2"
        # Check freshness values are computed
        assert ranked[0]["freshness"] > ranked[1]["freshness"]

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_source_weight_factor(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 3: Source weight factor.

        2 results with same similarity and freshness, different feed weights.
        Expect higher-weight feed article ranked higher (source_weight 1.0 vs 0.3 default).
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "High Weight Feed"},
            {"id": "id2", "pub_date": now.isoformat(), "feed_id": "feed2", "feed_name": "Low Weight Feed"},
        ]

        # Mock batch feed lookup - feed1 has weight 1.0, feed2 has no weight
        def get_feeds_by_ids_side_effect(feed_ids):
            result = {}
            for fid in feed_ids:
                mock_f = MagicMock()
                mock_f.weight = 1.0 if fid == "feed1" else None
                result[fid] = mock_f
            return result

        mock_get_feeds_by_ids.side_effect = get_feeds_by_ids_side_effect

        # Same distance and same pub_date for both
        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "High Weight Article", "url": "https://example.com/high", "distance": 0.5, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "Low Weight Article", "url": "https://example.com/low", "distance": 0.5, "document": "doc2"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 2
        # High weight feed article should be ranked first (source_weight 1.0 vs 0.3)
        assert ranked[0]["article_id"] == "a1"
        assert ranked[1]["article_id"] == "a2"
        # Check source_weight values
        assert ranked[0]["source_weight"] == 1.0
        assert ranked[1]["source_weight"] == 0.3

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_pre_v1_8_exclusion(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 4: Pre-v1.8 exclusion.

        2 results, one with sqlite_id=None, one with valid sqlite_id.
        Expect result with sqlite_id=None excluded from output.
        """
        from src.application.search import rank_semantic_results

        mock_get_articles_by_ids.return_value = [
            {"id": "id2", "pub_date": datetime.now(timezone.utc).isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
        ]
        mock_get_feeds_by_ids.return_value = {"feed1": MagicMock(weight=None)}

        results = [
            {"article_id": "a1", "sqlite_id": None, "title": "Old Article (pre-v1.8)", "url": "https://example.com/old", "distance": 0.2, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "New Article", "url": "https://example.com/new", "distance": 0.5, "document": "doc2"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        # Only the article with valid sqlite_id should be included
        assert len(ranked) == 1
        assert ranked[0]["article_id"] == "a2"

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_combined_score_calculation(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 5: Combined score calculation.

        Verify final_score = 0.5 * norm_similarity + 0.3 * norm_freshness + 0.2 * source_weight
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
        ]

        # Mock feed with weight 1.0
        mock_feed = MagicMock()
        mock_feed.weight = 1.0
        mock_get_feeds_by_ids.return_value = {"feed1": mock_feed}

        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "Article 1", "url": "https://example.com/article", "distance": 0.0, "document": "doc1"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 1
        r = ranked[0]

        # distance = 0.0 -> cos_sim = 1.0
        # Since there's only one result, norm_similarity = 1.0 (max == min)
        # freshness = 1.0 (published today)
        # source_weight = 1.0 (from feed)
        expected_final_score = 0.5 * 1.0 + 0.3 * 1.0 + 0.2 * 1.0
        assert abs(r["final_score"] - expected_final_score) < 0.001
        assert r["cos_sim"] == 1.0
        assert r["norm_similarity"] == 1.0
        assert r["norm_freshness"] == 1.0
        assert r["source_weight"] == 1.0

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_top_k_parameter(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 6: top_k parameter.

        5 results, top_k=3. Expect only 3 results returned.
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": f"id{i}", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"}
            for i in range(1, 6)
        ]
        mock_get_feeds_by_ids.return_value = {"feed1": MagicMock(weight=None)}

        results = [
            {"article_id": f"a{i}", "sqlite_id": f"id{i}", "title": f"Article {i}", "url": f"https://example.com/a{i}", "distance": 0.1 * i, "document": f"doc{i}"}
            for i in range(1, 6)
        ]

        ranked = rank_semantic_results(results, top_k=3)

        assert len(ranked) == 3

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_min_max_normalization_edge_case(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test Case 7: Min-max normalization edge case.

        All results have same distance (same cos_sim).
        Expect norm_similarity = 1.0 for all (fallback when max == min).
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
            {"id": "id2", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
            {"id": "id3", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Test Feed"},
        ]
        mock_get_feeds_by_ids.return_value = {"feed1": MagicMock(weight=None)}

        # All have the same distance
        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "Article 1", "url": "https://example.com/a1", "distance": 0.5, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "Article 2", "url": "https://example.com/a2", "distance": 0.5, "document": "doc2"},
            {"article_id": "a3", "sqlite_id": "id3", "title": "Article 3", "url": "https://example.com/a3", "distance": 0.5, "document": "doc3"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 3
        # All should have norm_similarity = 1.0 since max == min
        for r in ranked:
            assert r["norm_similarity"] == 1.0

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_feed_weight_ranking(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test that feed-based weight ranking works correctly.

        Different feeds have different weights, higher weight feeds rank higher.
        """
        from src.application.search import rank_semantic_results

        now = datetime.now(timezone.utc)

        # Mock batch article lookup
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": now.isoformat(), "feed_id": "feed1", "feed_name": "Feed 1"},
            {"id": "id2", "pub_date": now.isoformat(), "feed_id": "feed2", "feed_name": "Feed 2"},
            {"id": "id3", "pub_date": now.isoformat(), "feed_id": "feed3", "feed_name": "Feed 3"},
            {"id": "id4", "pub_date": now.isoformat(), "feed_id": "feed4", "feed_name": "Feed 4"},
        ]

        # Mock batch feed lookup - feed1: weight 1.0, feed2: weight 0.5, feed3/feed4: weight None (0.3 default)
        def get_feeds_by_ids_side_effect(feed_ids):
            result = {}
            for fid in feed_ids:
                mock_f = MagicMock()
                if fid == "feed1":
                    mock_f.weight = 1.0
                elif fid == "feed2":
                    mock_f.weight = 0.5
                else:
                    mock_f.weight = None
                result[fid] = mock_f
            return result

        mock_get_feeds_by_ids.side_effect = get_feeds_by_ids_side_effect

        # All have same distance (0.3) so ranking is determined by feed weight
        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "High Weight Feed", "url": "https://example.com/high", "distance": 0.3, "document": "doc1"},
            {"article_id": "a2", "sqlite_id": "id2", "title": "Medium Weight Feed", "url": "https://example.com/med", "distance": 0.3, "document": "doc2"},
            {"article_id": "a3", "sqlite_id": "id3", "title": "Low Weight Feed", "url": "https://example.com/low", "distance": 0.3, "document": "doc3"},
            {"article_id": "a4", "sqlite_id": "id4", "title": "Default Weight Feed", "url": "https://example.com/def", "distance": 0.3, "document": "doc4"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 4
        # feed1 (1.0) > feed2 (0.5) > feed3/feed4 (0.3)
        assert ranked[0]["article_id"] == "a1"   # weight 1.0
        assert ranked[1]["article_id"] == "a2"   # weight 0.5
        assert ranked[0]["source_weight"] == 1.0
        assert ranked[1]["source_weight"] == 0.5
        # feed3 and feed4 both have default 0.3, order may vary
        assert ranked[2]["source_weight"] == 0.3
        assert ranked[3]["source_weight"] == 0.3

    @patch("src.application.search.get_feeds_by_ids")
    @patch("src.application.search.get_articles_by_ids")
    def test_article_without_pub_date(self, mock_get_articles_by_ids, mock_get_feeds_by_ids):
        """Test that articles without pub_date get freshness = 0.0."""
        from src.application.search import rank_semantic_results

        # Mock batch article lookup - article without pub_date
        mock_get_articles_by_ids.return_value = [
            {"id": "id1", "pub_date": None, "feed_id": "feed1", "feed_name": "Test Feed"},
        ]

        mock_feed = MagicMock()
        mock_feed.weight = None
        mock_get_feeds_by_ids.return_value = {"feed1": mock_feed}

        results = [
            {"article_id": "a1", "sqlite_id": "id1", "title": "No Date Article", "url": "https://example.com/nodate", "distance": 0.3, "document": "doc1"},
        ]

        ranked = rank_semantic_results(results, top_k=10)

        assert len(ranked) == 1
        assert ranked[0]["freshness"] == 0.0
        assert ranked[0]["norm_freshness"] == 0.0
