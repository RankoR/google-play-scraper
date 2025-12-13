import asyncio

from google_play_scraper import GooglePlayClient


async def amain():
    client = GooglePlayClient()
    term = "todo list"

    print(f"Searching for: '{term}' (Free apps only)...")

    # Search returns a list of AppOverview objects
    results = await client.asearch(
        term=term,
        num=5,
        price="free",
        lang="en",
        country="us",
    )

    if not results:
        print("No results found.")
        return

    for idx, app in enumerate(results, 1):
        print(f"{idx}. {app.title}")
        print(f"   ID:    {app.app_id}")
        print(f"   Dev:   {app.developer}")
        print(f"   Score: {app.score}")
        print("-" * 30)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
