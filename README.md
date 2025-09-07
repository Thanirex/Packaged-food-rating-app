# 🍓 NutriScore-AI: Food Product Health Scanner

NutriScore-AI is a tool that scans a food product's barcode, fetches its nutritional information, and provides an easy-to-understand health score and summary. It uses official UK government guidelines for its core logic and a generative AI model to provide consumer-friendly explanations.

---

## 🏗️ High-Level Architecture

The application follows a simple, sequential data flow from data ingestion to user-facing explanation.

### Modules
* 📸 **Barcode Scanner** (`ui.py`): Uses **OpenCV** and **Pyzbar** to access the device camera and decode a product barcode from the live video stream.
* 🌐 **Data Fetcher** (`ui.py`): Takes the decoded barcode and queries the **OpenFoodFacts API** to retrieve detailed product information, including crucial nutritional values per 100g.
* ✨ **Normalizer** (`ui.py`): Cleans the raw API data, extracting only the four key nutrients (fat, saturates, sugars, salt) required for scoring and ensuring a consistent format.
* 🧮 **Scoring Engine** (`ui.py`): The core logic. It classifies each nutrient value as 'green', 'amber', or 'red' based on thresholds defined in `scoring_rules.json`. It then calculates a weighted final score out of 100.
* 🤖 **Explanation Generator** (`ui.py`): Sends the final score and nutrient breakdown to the **Google Gemini API** to generate a short, easy-to-understand comment about the product's health profile.
* 🖥️ **User Interface** (`ui.py`): A **Streamlit** web application that orchestrates the workflow and presents the final analysis to the user with visualizations.

### Data Flow
```mermaid
graph TD;
    A[Camera] -->|Barcode String| B(Data Fetcher);
    B -->|Raw Product JSON| C(Normalizer);
    C -->|Key Nutrients Dict| D(Scoring Engine);
    D -->|Scored Results JSON| E(Explanation Generator);
    E -->|AI Comment String| F(UI);
    F --> G[Final Analysis Page];
````

### I/O Schemas for Key Functions

#### `fetch_openfoodfacts_nutrition(barcode: str) -> dict`

  * **Input:** A string containing the product barcode (e.g., `"8886467124723"`).
  * **Output:** A JSON dictionary with product metadata and nutrition facts.

<!-- end list -->

```json
{
  "source": "OpenFoodFacts",
  "barcode": "8886467124723",
  "name": "Potato Chips",
  "nutrition_per_100g": {
    "Fat (g)": 30.9,
    "Saturated Fat (g)": 15.0,
    "Sugars (g)": 3.2,
    "Salt (g)": 1.605
  }
}
```

#### `score_product(product_data: dict, rules: dict) -> dict`

  * **Input:** A dictionary with normalized nutrient data and the scoring rules JSON.
  * **Output:** A JSON dictionary with the final score, band, and breakdown.

<!-- end list -->

```json
{
  "product": "Potato Chips",
  "score": 40.0,
  "band": "Amber Band",
  "results": {
    "sugars": { "value_per_100g": 3.2, "band": "green", "weighted_score": 40.0 },
    "saturates": { "value_per_100g": 15.0, "band": "red", "weighted_score": 0.0 }
  }
}
```

-----

## 🎯 Scoring Design

The scoring system converts complex nutritional data into a single, intuitive health score based on UK regulatory guidance.

  * **What the Score Means:** The score ranges from **0 to 100**, where **100 is the healthiest** and **0 is the least healthy**. It's based on four key nutrients: **fat, saturated fat, total sugars, and salt**.

  * **Scoring Bands:** The final score falls into one of three bands, as defined in `scoring_rules.json`:

      * 🟢 **Green Band (Healthy choice):** Score 70-100
      * 🟡 **Amber Band (Moderate health profile):** Score 40-69
      * 🔴 **Red Band (Less healthy choice):** Score 0-39

  * **Guardrails & Logic:**

      * The thresholds for Green/Amber/Red are taken directly from the UK's Front-of-Pack (FoP) guidance.
      * Each nutrient is assigned a weight in `scoring_rules.json` to reflect its relative health impact (sugars: 40%, saturates: 25%, salt: 20%, fat: 15%).
      * The final score is calculated as: `Σ (NutrientBandScore * NutrientWeight)`.
      * **Limitation:** The score does not account for positive nutrients like fiber, protein, or vitamins.

-----

## 🚀 Installation and Execution

Follow these steps to run the application on a clean machine.

### 1\. Installation Steps

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/Thanirex/Packaged-food-rating-app.git
    cd Packaged-food-rating-app
    ```

2.  **Create and Activate a Virtual Environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    *(Note: You will need to generate a `requirements.txt` file from your environment using `pip freeze > requirements.txt`)*

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key:**
    The application reads the Gemini API key from an environment variable.

    **On macOS/Linux:**

    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

    **On Windows (PowerShell):**

    ```powershell
    $env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

### 2\. Reproducible Run Command

With the environment activated and configured, run the following single command to start the web application:

```bash
streamlit run ui.py
```

This command starts the web server, opens the app in your browser, and makes all functionality available for an end-to-end run.

-----

## 📊 Outputs and Refreshing

### Where Outputs Appear

  * **On-Screen UI:** All primary results are displayed directly on the **Streamlit** web interface.
  * **Run Log (Console):** The terminal running the Streamlit app shows a log of activities, API status, and errors. The `FinalBackend.ipynb` notebook also produces a detailed console trace.
  * **JSON Artifacts:** The backend notebook saves raw fetched data to a file named `{barcode}_data.json`.

### How to Refresh a Cached Record

The app holds the last scanned result in its session state. To analyze a new product:

  * Click the "📷 **Scan from Camera**" button in the sidebar.
  * Or, enter a new barcode in the "**Manual Input**" field and click "**Analyze**".

-----

## ⚙️ Config Sample

The application requires one secret: the **Google Gemini API Key**. It must be set as an environment variable. All non-secret parameters for the scoring logic are contained in `scoring_rules.json`.

-----

# Watch the Explanation video here!:
https://drive.google.com/file/d/1HZ-p_guv1nEtKSkRtjA3JX5AAdnHVEd7/view?usp=sharing

-----

## 📚 Citations for Medical/Regulatory References

The scoring logic and nutritional thresholds are based on the following authoritative sources:

1.  **Primary Regulatory Guidance:**

      * [Guide to creating a front of pack (FoP) nutrition label for pre-packed products sold through retail outlets](https://www.gov.uk/government/publications/front-of-pack-nutrition-labelling-guidance). (2016). *Department of Health & Food Standards Agency, GOV.UK*.

2.  **European Union Legislation:**

      * [REGULATION (EU) No 1169/2011 on the provision of food information to consumers](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32011R1169). (2011). *Official Journal of the European Union*.

3.  **Global Health Recommendations:**

      * [Guideline: Sugars intake for adults and children](https://www.who.int/publications/i/item/9789241549028). (2015). *World Health Organization (WHO)*.

<!-- end list -->

```
```
