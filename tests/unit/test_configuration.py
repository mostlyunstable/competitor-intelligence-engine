import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.configuration.loader import ConfigurationLoader
from app.configuration.models import (
    CollectionFrequency,
    CollectionModule,
    CompetitorConfig,
    CompetitorsFile,
)
from app.configuration.settings import (
    CollectorSettings,
    DatabaseSettings,
    SchedulerSettings,
    Settings,
    get_settings,
    reset_settings,
)


class TestDatabaseSettings:
    def test_defaults(self) -> None:
        settings = DatabaseSettings()
        assert "postgresql" in settings.url
        assert settings.echo is False
        assert settings.pool_size == 10
        assert settings.max_overflow == 20
        assert settings.pool_timeout == 30
        assert settings.pool_recycle == 1800

    def test_custom_values(self) -> None:
        settings = DatabaseSettings(
            url="postgresql+asyncpg://user:pass@host:5432/db",
            echo=True,
            pool_size=20,
            max_overflow=40,
        )
        assert settings.url == "postgresql+asyncpg://user:pass@host:5432/db"
        assert settings.echo is True
        assert settings.pool_size == 20
        assert settings.max_overflow == 40


class TestCollectorSettings:
    def test_defaults(self) -> None:
        settings = CollectorSettings()
        assert settings.max_concurrent_requests == 10
        assert settings.collection_timeout == 300
        assert settings.rate_limit_per_second == 0.5
        assert settings.user_agent == "UtservioCI/1.0"
        assert settings.retry_attempts == 3
        assert settings.retry_delay == 1.0

    def test_validation_bounds(self) -> None:
        with pytest.raises(ValidationError):
            CollectorSettings(max_concurrent_requests=0)
        with pytest.raises(ValidationError):
            CollectorSettings(max_concurrent_requests=101)
        with pytest.raises(ValidationError):
            CollectorSettings(collection_timeout=10)
        with pytest.raises(ValidationError):
            CollectorSettings(rate_limit_per_second=0.01)


class TestSchedulerSettings:
    def test_defaults(self) -> None:
        settings = SchedulerSettings()
        assert settings.enabled is True
        assert settings.check_interval_seconds == 60

    def test_custom(self) -> None:
        settings = SchedulerSettings(enabled=False, check_interval_seconds=120)
        assert settings.enabled is False
        assert settings.check_interval_seconds == 120


class TestSettings:
    def test_singleton(self) -> None:
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset(self) -> None:
        reset_settings()
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2

    def test_defaults(self) -> None:
        reset_settings()
        settings = get_settings()
        assert settings.environment == "development"
        assert settings.log_level == "info"
        assert settings.debug is False
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.collector, CollectorSettings)
        assert isinstance(settings.scheduler, SchedulerSettings)

    def test_env_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CI_ENVIRONMENT", "production")
        monkeypatch.setenv("CI_DEBUG", "true")
        reset_settings()
        settings = Settings(_env_file=None)
        assert settings.environment == "production"
        assert settings.debug is True

    def test_nested_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CI_DATABASE__ECHO", "true")
        monkeypatch.setenv("CI_COLLECTOR__MAX_CONCURRENT_REQUESTS", "5")
        reset_settings()
        settings = Settings(_env_file=None)
        assert settings.database.echo is True
        assert settings.collector.max_concurrent_requests == 5


class TestCollectionFrequency:
    def test_values(self) -> None:
        assert CollectionFrequency.HOURLY.value == "hourly"
        assert CollectionFrequency.DAILY.value == "daily"
        assert CollectionFrequency.WEEKLY.value == "weekly"

    def test_all_members(self) -> None:
        assert len(CollectionFrequency) == 3


class TestCollectionModule:
    def test_values(self) -> None:
        assert CollectionModule.DISCOVERY.value == "discovery"
        assert CollectionModule.COMPANY.value == "company"
        assert CollectionModule.SERVICES.value == "services"
        assert CollectionModule.PRICING.value == "pricing"
        assert CollectionModule.CONTENT.value == "content"
        assert CollectionModule.SOCIAL.value == "social"

    def test_all_members(self) -> None:
        assert len(CollectionModule) == 6


class TestCompetitorConfig:
    def test_valid_config(self) -> None:
        config = CompetitorConfig(
            name="Test Corp",
            website_url="https://test.com",
        )
        assert config.name == "Test Corp"
        assert config.website_url == "https://test.com"
        assert config.enabled is True
        assert config.collection_frequency == CollectionFrequency.DAILY
        assert len(config.modules) == len(CollectionModule)

    def test_minimal_config(self) -> None:
        config = CompetitorConfig(
            name="A",
            website_url="http://a.com",
        )
        assert config.name == "A"
        assert config.enabled is True

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(website_url="https://test.com")  # type: ignore[call-arg]

    def test_name_min_length(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(name="", website_url="https://test.com")

    def test_name_max_length(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(name="x" * 256, website_url="https://test.com")

    def test_url_must_be_http(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(name="Test", website_url="ftp://test.com")

    def test_url_must_be_valid(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(name="Test", website_url="not-a-url")

    def test_custom_modules(self) -> None:
        config = CompetitorConfig(
            name="Test Corp",
            website_url="https://test.com",
            modules=[CollectionModule.COMPANY, CollectionModule.PRICING],
        )
        assert len(config.modules) == 2
        assert CollectionModule.COMPANY in config.modules

    def test_custom_tags(self) -> None:
        config = CompetitorConfig(
            name="Test Corp",
            website_url="https://test.com",
            tags=["home-services", "warranty"],
        )
        assert config.tags == ["home-services", "warranty"]

    def test_notes_max_length(self) -> None:
        config = CompetitorConfig(
            name="Test Corp",
            website_url="https://test.com",
            notes="x" * 1000,
        )
        assert len(config.notes) == 1000

    def test_notes_too_long(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorConfig(
                name="Test Corp",
                website_url="https://test.com",
                notes="x" * 1001,
            )

    def test_disabled_competitor(self) -> None:
        config = CompetitorConfig(
            name="Disabled Corp",
            website_url="https://disabled.com",
            enabled=False,
        )
        assert config.enabled is False

    def test_weekly_frequency(self) -> None:
        config = CompetitorConfig(
            name="Weekly Corp",
            website_url="https://weekly.com",
            collection_frequency=CollectionFrequency.WEEKLY,
        )
        assert config.collection_frequency == CollectionFrequency.WEEKLY


class TestCompetitorsFile:
    def test_empty_file(self) -> None:
        file = CompetitorsFile()
        assert len(file.competitors) == 0

    def test_multiple_competitors(self) -> None:
        file = CompetitorsFile(
            competitors=[
                CompetitorConfig(name="A", website_url="https://a.com"),
                CompetitorConfig(name="B", website_url="https://b.com"),
            ]
        )
        assert len(file.competitors) == 2


class TestConfigurationLoader:
    def test_load_valid_file(self, tmp_path: Path) -> None:
        config_data = {
            "competitors": [
                {
                    "name": "Test Corp",
                    "website_url": "https://test.com",
                    "enabled": True,
                    "collection_frequency": "daily",
                    "modules": ["company", "services"],
                    "tags": ["test"],
                    "notes": "Test notes",
                }
            ]
        }
        config_file = tmp_path / "competitors.json"
        config_file.write_text(json.dumps(config_data))

        loader = ConfigurationLoader(config_file)
        competitors = loader.load()

        assert len(competitors) == 1
        assert competitors[0].name == "Test Corp"
        assert competitors[0].website_url == "https://test.com"
        assert competitors[0].enabled is True
        assert competitors[0].collection_frequency == CollectionFrequency.DAILY
        assert len(competitors[0].modules) == 2
        assert competitors[0].tags == ["test"]

    def test_load_missing_file(self, tmp_path: Path) -> None:
        loader = ConfigurationLoader(tmp_path / "nonexistent.json")
        competitors = loader.load()
        assert len(competitors) == 0

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.json"
        config_file.write_text("not valid json {{{")

        loader = ConfigurationLoader(config_file)
        competitors = loader.load()
        assert len(competitors) == 0

    def test_load_invalid_schema(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad_schema.json"
        config_file.write_text(json.dumps({"competitors": [{"name": ""}]}))

        loader = ConfigurationLoader(config_file)
        competitors = loader.load()
        assert len(competitors) == 0

    def test_get_competitor_by_name(self, tmp_path: Path) -> None:
        config_data = {
            "competitors": [
                {"name": "Alpha", "website_url": "https://alpha.com"},
                {"name": "Beta", "website_url": "https://beta.com"},
            ]
        }
        config_file = tmp_path / "competitors.json"
        config_file.write_text(json.dumps(config_data))

        loader = ConfigurationLoader(config_file)
        loader.load()

        alpha = loader.get_competitor_by_name("Alpha")
        assert alpha is not None
        assert alpha.name == "Alpha"

        missing = loader.get_competitor_by_name("Gamma")
        assert missing is None

    def test_get_competitors_returns_copy(self, tmp_path: Path) -> None:
        config_data = {
            "competitors": [
                {"name": "Test", "website_url": "https://test.com"},
            ]
        }
        config_file = tmp_path / "competitors.json"
        config_file.write_text(json.dumps(config_data))

        loader = ConfigurationLoader(config_file)
        loader.load()

        competitors1 = loader.get_competitors()
        competitors2 = loader.get_competitors()
        assert competitors1 is not competitors2
        assert len(competitors1) == len(competitors2)

    def test_reload(self, tmp_path: Path) -> None:
        config_file = tmp_path / "competitors.json"
        config_file.write_text(
            json.dumps({"competitors": [{"name": "V1", "website_url": "https://v1.com"}]})
        )

        loader = ConfigurationLoader(config_file)
        loader.load()
        assert len(loader.get_competitors()) == 1

        config_file.write_text(
            json.dumps(
                {
                    "competitors": [
                        {"name": "V2a", "website_url": "https://v2a.com"},
                        {"name": "V2b", "website_url": "https://v2b.com"},
                    ]
                }
            )
        )
        loader.reload()
        assert len(loader.get_competitors()) == 2
        assert loader.get_competitor_by_name("V2a") is not None

    def test_empty_competitors_list(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.json"
        config_file.write_text(json.dumps({"competitors": []}))

        loader = ConfigurationLoader(config_file)
        competitors = loader.load()
        assert len(competitors) == 0

    def test_load_multiple_competitors(self, tmp_path: Path) -> None:
        config_data = {
            "competitors": [
                {"name": f"Competitor {i}", "website_url": f"https://comp{i}.com"}
                for i in range(10)
            ]
        }
        config_file = tmp_path / "competitors.json"
        config_file.write_text(json.dumps(config_data))

        loader = ConfigurationLoader(config_file)
        competitors = loader.load()
        assert len(competitors) == 10

    def test_string_path(self, tmp_path: Path) -> None:
        config_file = tmp_path / "competitors.json"
        config_file.write_text(
            json.dumps({"competitors": [{"name": "Test", "website_url": "https://test.com"}]})
        )

        loader = ConfigurationLoader(str(config_file))
        competitors = loader.load()
        assert len(competitors) == 1
