from openai import OpenAI
from config import MODEL, BASE_URL, API_KEY

_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def chat(prompt: str, temperature: float = 0.7, top_p: float = 1.0, model: str = MODEL) -> str:
    """로컬 Ollama에 단일 프롬프트를 보내고 응답 텍스트를 반환한다."""
    response = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "반드시 한국어로만 답변하세요."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        top_p=top_p,
    )
    return response.choices[0].message.content.strip()
