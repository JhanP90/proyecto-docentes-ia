import os
import json
from pydantic import BaseModel, Field
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

class MySchema(BaseModel):
    name: str = Field(default="John", description="The name")
    age: int = Field(default=30)

print("JSON Schema:")
print(json.dumps(MySchema.model_json_schema(), indent=2))

try:
    genai.configure(api_key="mock")
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=MySchema,
        )
    )
    print("Model initialized successfully with response_schema.")
except Exception as e:
    print("Error initializing model:", type(e).__name__, e)
