"""Tests for TLDRChain."""

import pytest

from src.application.report.models import ReportCluster, ReportData
from src.application.report.tldr import TLDRChain


class TestTLDRChainInit:
    def test_tldr_chain_default_init(self):
        chain = TLDRChain()
        assert chain.top_n == 100
        assert chain.target_lang == "zh"
        assert chain.batch_size == 20
        assert chain.max_concurrency == 5

    def test_tldr_chain_custom_init(self):
        chain = TLDRChain(top_n=50, target_lang="en", batch_size=10, max_concurrency=3)
        assert chain.top_n == 50
        assert chain.target_lang == "en"
        assert chain.batch_size == 10
        assert chain.max_concurrency == 3


class TestTLDRChainHelpers:
    def test_flatten_clusters_empty(self):
        chain = TLDRChain()
        result = chain._flatten_clusters([])
        assert result == []

    def test_flatten_clusters_no_children(self):
        chain = TLDRChain()
        cluster = ReportCluster(name="test", articles=[])
        result = chain._flatten_clusters([cluster])
        assert len(result) == 1
        assert result[0].name == "test"

    def test_flatten_clusters_with_children(self):
        chain = TLDRChain()
        child = ReportCluster(name="child", articles=[])
        parent = ReportCluster(name="parent", articles=[], children=[child])
        result = chain._flatten_clusters([parent])
        assert len(result) == 2
        names = [c.name for c in result]
        assert "parent" in names
        assert "child" in names

    def test_collect_all_clusters(self):
        chain = TLDRChain()
        cluster1 = ReportCluster(name="c1", articles=[])
        cluster2 = ReportCluster(name="c2", articles=[])
        clusters = {"group1": [cluster1], "group2": [cluster2]}
        result = chain._collect_all_clusters(clusters)
        assert len(result) == 2

    def test_build_topics_block_empty(self):
        chain = TLDRChain()
        result = chain._build_topics_block([])
        assert result == ""

    def test_build_topics_block_single_cluster(self):
        from src.application.articles import ArticleListItem

        chain = TLDRChain()
        article = ArticleListItem(
            id="1",
            feed_id="1",
            feed_name="Test Feed",
            title="Test Article",
            link="http://example.com",
            guid="abc",
            published_at=None,
            description=None,
        )
        cluster = ReportCluster(name="Tech", articles=[article])
        result = chain._build_topics_block([cluster])
        assert "Entity 1 (Tech): Test Article" in result

    def test_build_topics_block_uses_translation(self):
        from src.application.articles import ArticleListItem

        chain = TLDRChain()
        article = ArticleListItem(
            id="1",
            feed_id="1",
            feed_name="Test Feed",
            title="Test",
            link="http://example.com",
            guid="abc",
            published_at=None,
            description=None,
        )
        article.translation = "Translated Title"
        cluster = ReportCluster(name="Tech", articles=[article])
        result = chain._build_topics_block([cluster])
        assert "Translated Title" in result


class TestTLDRChainAinvoke:
    def test_ainvoke_empty_clusters(self):
        import asyncio

        chain = TLDRChain()
        report_data = ReportData(clusters={}, date_range={})
        result = asyncio.get_event_loop().run_until_complete(chain.ainvoke(report_data))
        assert result is report_data

    def test_ainvoke_clusters_without_articles(self):
        import asyncio

        chain = TLDRChain()
        cluster = ReportCluster(name="empty", articles=[])
        report_data = ReportData(clusters={"group": [cluster]}, date_range={})
        result = asyncio.get_event_loop().run_until_complete(chain.ainvoke(report_data))
        assert result is report_data
        # summary may be None or empty string depending on LLM call result
        assert result.clusters["group"][0].summary in (None, "")

    def test_ainvoke_clusters_with_articles_no_llm(self):
        """Test that clusters with articles are processed (LLM call may fail gracefully)."""
        import asyncio

        chain = TLDRChain()
        from src.application.articles import ArticleListItem

        article = ArticleListItem(
            id="1",
            feed_id="1",
            feed_name="Test Feed",
            title="Test Article",
            link="http://example.com",
            guid="abc",
            published_at=None,
            description=None,
        )
        cluster = ReportCluster(name="Tech", articles=[article])
        report_data = ReportData(clusters={"group": [cluster]}, date_range={})

        # Should not raise, even if LLM call fails
        result = asyncio.get_event_loop().run_until_complete(chain.ainvoke(report_data))
        assert result is report_data


class TestTLDRChainInvoke:
    def test_sync_invoke(self):
        chain = TLDRChain()
        report_data = ReportData(clusters={}, date_range={})
        result = chain.invoke(report_data)
        assert result is report_data


class TestTLDRChainBatch:
    def test_abatch_single_input(self):
        import asyncio

        chain = TLDRChain()
        report_data = ReportData(clusters={}, date_range={})
        result = asyncio.get_event_loop().run_until_complete(
            chain.abatch([report_data])
        )
        assert len(result) == 1
        assert result[0] is report_data

    def test_sync_batch(self):
        chain = TLDRChain()
        report_data = ReportData(clusters={}, date_range={})
        result = chain.batch([report_data])
        assert len(result) == 1
        assert result[0] is report_data
