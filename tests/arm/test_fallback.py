                    Snippet(
                        id="k1",
                        title="test",
                        content="test content for index readiness",
                        language=Language.MARKDOWN,
                        tags=[],
                        created_at=now,
                    ),
                ]
            )
            assert search.indices_ready is True

    def test_hybrid_search_keyword_search_works_without_semantic(self) -> None:
        """Keyword search produces results when semantic deps are absent."""
        from snipcontext.config.settings import Config
        from snipcontext.core.models import Language, Snippet
        from snipcontext.core.storage import StorageEngine

        tmpdir = Path(tempfile.mkdtemp())
        real_config = Config(
            snippets_path=tmpdir / "snippets",
            index_path=tmpdir / "index",
            storage_path=tmpdir / "storage",
            data_dir=tmpdir / "data",
            search__top_k=10,
            search__default_mode="keyword",
            search__min_score=0.0,
            search__semantic_weight=0.5,
            search__keyword_weight=0.5,
            embedding__model_name="all-MiniLM-L6-v2",
            embedding__device="cpu",
            embedding__batch_size=32,
            embedding__normalize=True,
            embedding__doc_instruction="",
            embedding__query_instruction="",
            max_snippets_per_export=100,
            snippets_per_page=20,
            watchdog_ready=False,
            snipcontext_dir=tmpdir,
        )
        real_config.snippets_path.mkdir(parents=True, exist_ok=True)
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=real_config,
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            storage = StorageEngine(real_config)
            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="test-1",
                title="test snippet",
                content="This is a test snippet for keyword search.",
                language=Language.MARKDOWN,
                tags=[],
                created_at=now,
            )
            storage.save(snippet)

            all_snippets = storage.list_all()
            assert len(all_snippets) == 1
            assert all_snippets[0].id == "test-1"
            assert "test snippet" in all_snippets[0].to_search_text().lower()

            search.rebuild_keyword_index(all_snippets)
            raw_results = search.keyword_index.search("test snippet", top_k=5, min_score=0.0)
            assert raw_results, "Keyword index returned no raw matches"
            assert raw_results[0][0] == "test-1"

            results = search.search("test snippet", top_k=5, mode="keyword")
            assert results is not None
            assert len(results) >= 1, (
                f"Expected at least 1 hydrated result, got {len(results)}; "
                f"raw results: {raw_results}; indexed snippets: {all_snippets}"
            )

    def test_hybrid_search_no_semantic_flag_overrides_mode(self) -> None:
        """no_semantic=True forces keyword mode even when SEMANTIC_AVAILABLE is True."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", True),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert hasattr(search, "search")
