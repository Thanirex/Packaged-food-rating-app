Project Checkpoint 2: Rulebook, Scoring, and LLM Integration
Current Status
The project has now moved past early experiments and into a structured, end-to-end pipeline. At this point:

Rulebook completed: A JSON rulebook (scoring_rules.json) built from authoritative standards (UK FoP labelling, EU regulations, WHO guidelines).

Scoring engine implemented: Nutrients are classified into green/amber/red using thresholds, weighted, and aggregated into a 0–100 health score with bands.

Normalization layer ready: API outputs from OpenFoodFacts and USDA are standardized so scoring always runs on consistent input.

LLM commentary integrated: Gemini API generates short, consumer-friendly explanations based on the calculated score.

This means I can now scan a product, retrieve its nutrition, normalize the data, compute a health score, and get a plain-language explanation in one pipeline.

Development Journey
Rulebook and Scoring
Built scoring_rules.json with thresholds, nutrient weights, and evidence sources. Developed a robust parser to handle conditions like >5 and <=22.5, ensuring the engine works across varied products.

Normalization
Mapped diverse nutrition keys (e.g. "Sugars (g)", "sugars") into canonical forms so scoring is reliable across different APIs.

Commentary with Gemini
Once scores are computed, they are passed to Gemini for explanation. This adds clarity by summarizing why a product is rated healthy, moderate, or less healthy, and referencing evidence sources.

Architecture at This Stage
Data Extraction

Webcam barcode scan.

Nutrition data fetched from OpenFoodFacts / USDA.

Raw JSON saved per barcode.

Normalization

Keys mapped to a consistent schema.

Output is standardized nutrition data.

Scoring

Rulebook thresholds applied.

Product scored 0–100 and assigned a health band.

LLM Commentary

Gemini explains the result in plain language.

Explanation highlights why the product received its score and which source guided the decision.

Next Step
The next development milestone is to build a UI interface:

Camera integration to scan the barcode directly from the app.

A health bar visualization that displays the product’s score and band.

Inline commentary from Gemini showing why the product was scored that way.

Clear attribution of the evidence source (e.g., UK FoP, WHO guidelines).

This will transform the backend pipeline into a usable application for end users.

CHECKPOINT 1:
🎯 Current Status & My Next Hurdle
Right now, I'm focused on building the core logic: the Rulebook and Scoring Engine.

My main challenge is finding a comprehensive and authoritative source to define the nutritional thresholds for what constitutes "low," "medium," or "high" levels of sugar, sodium, and saturated fat. My scoring engine's credibility depends entirely on the quality of this source.

My Research into Authoritative Sources:
I've been looking into several globally recognized standards to build my rulebook.json file:

WHO Guidelines: The World Health Organization is a strong candidate for global health standards.

FSSAI's Food Safety and Standards: Since I'm in India, using the FSSAI's regulations for front-of-pack labelling (FoPL) would be highly relevant and accurate for local products.

UK's Traffic Light System: This is a very clear and well-defined system that's easy to translate into scoring logic.

US FDA's Daily Value (DV%): This is another option, though it might require more work to convert percentages into direct thresholds.

Once I select a source, my next step is to codify its rules into a JSON file and then write the Python function that scores the normalized data against it.

🚀 My Development Journey & Learnings
This project has been a fantastic learning experience, evolving significantly as I've tackled different technical challenges.

Phase 1: The Naive Scraper and Hitting a Wall
My Initial Idea: I started with what I thought would be a simple approach. My first script used the requests library to download a product's webpage and BeautifulSoup to parse the HTML. The plan was to just search for the word "ingredients" and grab the text around it.

The Experience (Hitting a Wall): I immediately hit a wall. My script was consistently blocked with HTTP 403: Forbidden errors. This was my first real lesson in modern web scraping: sites like BigBasket have anti-bot systems. They can easily identify basic scripts because the default User-Agent header screams "I'm a Python script!" This approach was a dead end.

Phase 2: Advanced Scraping, A New Bug, and a Big Pivot
My Solution: To get around the blocking, I decided my script needed to act more like a real person. I upgraded my code to use Selenium with the undetected-chromedriver library.

The Code Explained: This was a major step up. Selenium automates an actual Chrome browser, so it naturally sends all the complex headers and executes JavaScript just like a human user. The undetected-chromedriver library adds extra patches to hide the automation flags that Selenium normally reveals, making it very difficult for sites to block.

The Experience (A New Frustrating Bug): Just when I thought I'd won, I hit a new, frustrating version mismatch error. I had hardcoded a ChromeDriver version in the script, and it no longer matched my auto-updated Chrome browser. My key learning here was to never hardcode environment-specific dependencies. I fixed this by removing the version number and letting the library handle auto-detection, which is a much more robust solution.

The Pivot (Realizing My Mistake): After getting the scraper to work, I had a major realization about the project's direction. My initial mistake was focusing solely on fetching the ingredients list. While interesting, ingredients are just unstructured blocks of text, making them incredibly difficult to score programmatically. When I shifted my goal to fetching nutritional information (calories, fat, sugar), the path forward became much clearer and easier. Nutritional data is inherently structured (e.g., 'Sugars: 10g') and is readily available from dedicated food APIs. This pivot from unstructured text (ingredients) to structured data (nutrition) was the key breakthrough that made building the new, reliable script much faster.

Phase 3: The API-First, "Safe" Architecture
My New Approach: I redesigned the project to be more professional and reliable. I'm now using an API-first approach based on the "Correct Safe Flow" I designed. This prioritizes accuracy and structure over brittle scraping.

The Code Explained: My first script now uses the requests library to call the OpenFoodFacts and USDA APIs. These services are designed for machine consumption and return clean, predictable JSON data. This is far superior to scraping. After fetching the data, the script saves the result into a [barcode]_data.json file, creating a clean checkpoint.

The Experience (The Power of Normalization): The next piece of code I wrote handles Normalization. It loads that JSON file and uses simple Python dictionaries as lookup tables to standardize all the data. For example, it converts keys like "Sugars (g)" into a simple, canonical key: "sugar". Writing this felt great because it reinforced a core software principle: create a clean, consistent data model before you build complex logic on top of it. This makes the next step—scoring—infinitely easier.

🛠️ The Architecture I'm Building
Here is the step-by-step architecture I'm currently implementing:

📸 Data Extraction (✅ I've completed this)

The script uses the webcam to read a barcode.

It queries APIs (OpenFoodFacts, USDA) for nutritional data.

The clean data is saved to a [barcode]_data.json file.

🧹 Normalization (✅ I've completed this)

A second script loads the JSON file.

It uses mapping dictionaries to standardize all nutrient and ingredient names.

The output is a normalized_data object, perfectly prepared for the next step.

📜 Rulebook & 🧮 Scoring Engine (🎯 This is my current focus)

I need to create a rulebook.json from an authoritative source and write the Python scoring logic.

🗣️ LLM for Explanation (🔲 This is next)

After the score is calculated, I'll pass the result (e.g., "Score: 42, High in Sodium") to an LLM to generate a simple, user-friendly explanation.

🖥️ User Interface (pencill; This is the final step)

To wrap it all up, I'll build a simple web or desktop app to display the final health score and explanation to the user.
