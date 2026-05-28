import os
import requests

from dotenv import load_dotenv


load_dotenv()


SUMMARY_API_URL = os.getenv("SUMMARY_API_URL")


def request_summary(transcript):

    response = requests.post(
        SUMMARY_API_URL,
        json={
            "transcript": transcript
        },
        timeout=120
    )

    return response.json()