def translate_text(message: str, target_language: str) -> str | None:
    import requests
    from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

    """
    Translates the given message to the target language using an external translation service.
    """
    try:
        url = ContextRegistry.get().get_settings().translation_api_url
        data = {
            "q": message,
            "source": "auto",
            "target": target_language,
            "format": "text",
        }
        response = requests.post(url, json=data)

        return response.json().get("translatedText", None)
    except requests.RequestException as e:
        print(f"An error occurred while making the request: {e}")
        return None
