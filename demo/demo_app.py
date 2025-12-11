from google_play_scraper import GooglePlayClient, AppNotFound


def main():
    # Initialize client (proxies can be set here)
    client = GooglePlayClient(country="us", lang="en")

    app_id = "com.nianticlabs.pokemongo"

    print(f"Fetching details for: {app_id}...")

    try:
        result = client.app(app_id)

        # Pretty print the Pydantic model
        print(result.model_dump_json(indent=2, exclude={"description_html", "comments"}))

        print("\n-------------------")
        print(f"Title:       {result.title}")
        print(f"Developer:   {result.developer}")
        print(f"Score:       {result.score}")
        print(f"Installs:    {result.min_installs}+")
        print(f"Updated:     {result.updated}")

    except AppNotFound:
        print(f"Error: App {app_id} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
