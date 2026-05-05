from services.gib_import.mock_dataset import build_mock_gib_payloads


class MockGibAdapter:
    source = 'mock_gib'

    async def fetch_payloads(self, **_kwargs):
        return build_mock_gib_payloads()
