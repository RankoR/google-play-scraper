import asyncio

from google_play_scraper import GooglePlayClient


async def amain():
    client = GooglePlayClient(country="us", lang="en")
    term = "watch face"

    print(f"Getting suggestions for '{term}'...")

    try:
        suggestions = await client.asuggest(term)

        print("Google Play suggests:")
        for s in suggestions:
            print(f"- {s}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
