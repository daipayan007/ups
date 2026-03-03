from openai import OpenAI
from llm import get_llm
endpoint = "https://UPS-FoundryResource1.openai.azure.com/openai/v1/"
deployment_name = "o3-mini"
api_key = "7f6fqNT1dndbpQpoeWOGT3i6wrb6hcsB2W6302bZkuOfY8zOT651JQQJ99CBACYeBjFXJ3w3AAAAACOGMp1b"

client = get_llm()

completion = client.invoke(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
    temperature=0.7,
)

print(completion.choices[0].message)