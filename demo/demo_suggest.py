from google_play_scraper import GooglePlayClient


def main():
    client = GooglePlayClient(country="us", lang="en")
    term = "watch face"

    print(f"Getting suggestions for '{term}'...")

    try:
        suggestions = client.suggest(term)

        print("Google Play suggests:")
        for s in suggestions:
            print(f"- {s}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
