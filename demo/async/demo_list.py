import asyncio

from google_play_scraper import GooglePlayClient, Collection, Category


async def amain():
    client = GooglePlayClient()

    print("Fetching Top Free Action Games...")

    # Fetch top 10 apps from the collection
    results = await client.alist(
        collection=Collection.TOP_FREE,
        category=Category.GAME_ACTION,
        num=10,
        age=None,
        lang="en",
        country="us",
    )

    for idx, app in enumerate(results, 1):
        print(f"#{idx} {app.title} ({app.price_text})")
        print(f"    ID: {app.app_id}")
        print(f"    Icon: {app.icon}")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
