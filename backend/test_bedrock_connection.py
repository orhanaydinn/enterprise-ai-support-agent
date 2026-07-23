import boto3
from botocore.exceptions import BotoCoreError, ClientError


AWS_REGION = "eu-west-2"
BEDROCK_MODEL_ID = "global.amazon.nova-2-lite-v1:0"


def test_bedrock_connection() -> None:
    """Send a minimal test request to Amazon Bedrock."""

    client = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
    )

    try:
        response = client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "Reply with exactly: "
                                "Bedrock connection successful"
                            )
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 30,
                "temperature": 0.0,
            },
        )

        output_blocks = response["output"]["message"]["content"]

        output_text = "".join(
            block.get("text", "")
            for block in output_blocks
            if "text" in block
        ).strip()

        print(f"Region: {AWS_REGION}")
        print(f"Model: {BEDROCK_MODEL_ID}")
        print(f"Response: {output_text}")

    except ClientError as error:
        error_details = error.response.get("Error", {})

        print(
            "AWS error code:",
            error_details.get("Code", "Unknown"),
        )
        print(
            "AWS error message:",
            error_details.get("Message", str(error)),
        )

    except BotoCoreError as error:
        print(f"AWS SDK error: {error}")

    except (KeyError, TypeError) as error:
        print(f"Unexpected response format: {error}")


if __name__ == "__main__":
    test_bedrock_connection()