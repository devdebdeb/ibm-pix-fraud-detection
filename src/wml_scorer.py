import json
import requests
from pathlib import Path


def get_iam_token(api_key: str) -> str:
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"apikey": api_key, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


class WMLScorer:
    def __init__(self, credentials_path: str = "config/credentials.json", scoring_url: str | None = None):
        with open(credentials_path) as f:
            creds = json.load(f)["wml"]
        # scoring_url comes from deployment_meta.json (notebook 04) and may be passed
        # explicitly; fall back to credentials.json for backward compatibility.
        url = scoring_url or creds.get("scoring_url")
        if not url:
            raise ValueError("scoring_url not provided and not present in credentials.json")
        # The WML v2 online scoring endpoint requires a version query parameter.
        if "version=" not in url:
            url += ("&" if "?" in url else "?") + "version=2021-05-01"
        self.scoring_url: str = url
        self._token = get_iam_token(creds["apikey"])

    def score(self, records: list[list]) -> list[dict]:
        """
        Args:
            records: list of feature vectors (each a list of floats)
        Returns:
            list of prediction dicts with keys 'prediction' and 'probability'
        """
        payload = {"input_data": [{"values": records}]}
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self.scoring_url, json=payload, headers=headers)
        resp.raise_for_status()
        results = resp.json()["predictions"][0]

        predictions = results["values"]
        return [
            {"prediction": int(p[0]), "probability": p[1]}
            for p in predictions
        ]

    def score_dataframe(self, df) -> list[dict]:
        """Convenience wrapper — accepts a pandas DataFrame of features."""
        return self.score(df.values.tolist())
