# NutriScore-AI: Food Product Health Scanner

NutriScore-AI is a tool that scans a food product's barcode, fetches its nutritional information, and provides an easy-to-understand health score and summary. It uses official UK government guidelines for its core logic and a generative AI model to provide consumer-friendly explanations.

---

## High-Level Architecture

The application follows a simple, sequential data flow from data ingestion to user-facing explanation.

### Modules

1.  **Barcode Scanner (`ui.py`):** Uses `OpenCV` and `Pyzbar` to access the device camera and decode a product barcode from the live video stream.
2.  **Data Fetcher (`ui.py`):** Takes the decoded barcode and queries the **OpenFoodFacts API** to retrieve detailed product information, including the crucial nutritional values per 100g.
3.  **Normalizer (`ui.py`):** Cleans the raw API data, extracting only the four key nutrients (fat, saturates, sugars, salt) required for scoring. It ensures the data is in a consistent format (float values).
4.  **Scoring Engine (`ui.py`):** The core logic. It classifies each nutrient value as 'green', 'amber', or 'red' based on thresholds defined in `scoring_rules.json`. It then calculates a weighted final score out of 100.
5.  **Explanation Generator (`ui.py`):** Sends the final score and nutrient breakdown to the **Google Gemini API**. It receives a short, easy-to-understand comment about the product's health profile.
6.  **User Interface (`ui.py`):** A **Streamlit** web application that orchestrates the workflow and presents the final analysis to the user with visualizations.

### Data Flow

[Camera] -> Barcode (string) -> [Data Fetcher] -> Raw Product Data (JSON) -> [Normalizer] -> Key Nutrients (dict) -> [Scoring Engine] -> Scored Results (JSON) -> [Explanation Generator] -> AI Comment (string) -> [UI] -> Final Analysis Page

### I/O Schemas for Key Functions

* **`fetch_openfoodfacts_nutrition(barcode: str) -> dict`**
    * **Input:** A string containing the product barcode (e.g., `"8886467124723"`).
    * **Output:** A JSON dictionary containing product metadata and nutrition facts. Example:
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

* **`score_product(product_data: dict, rules: dict) -> dict`**
    * **Input:** A dictionary with normalized nutrient data and the scoring rules JSON.
    * **Output:** A JSON dictionary with the final score, band, and detailed breakdown. Example:
        ```json
        {
          "product": "Potato Chips",
          "score": 40.0,
          "band": "Amber Band",
          "results": {
            "sugars": { "value_per_100g": 3.2, "band": "green", ... },
            "saturates": { "value_per_100g": 15.0, "band": "red", ... }
          }
        }
        ```

---

## Scoring Design

The scoring system is designed to convert complex nutritional data into a single, intuitive health score based on UK regulatory guidance.

* **What the Score Means:** The score ranges from **0 to 100**, where **100 is the healthiest** and **0 is the least healthy**. It is calculated based on the levels of four key nutrients that are recommended for limited consumption: **fat, saturated fat, total sugars, and salt.**

* **Scoring Bands:** The final score falls into one of three bands:
    * 🟢 **Green Band (Healthy):** Score 70-100
    * 🟡 **Amber Band (Moderate):** Score 40-69
    * 🔴 **Red Band (Less Healthy):** Score 0-39

* **Guardrails & Logic:**
    * The thresholds for Green/Amber/Red for each nutrient are taken directly from the UK's Front-of-Pack (FoP) guidance (see Citations).
    * Each nutrient is assigned a **weight** to reflect its relative health impact (e.g., sugars are weighted most heavily at 40%).
    * `Final Score = Σ (NutrientBandScore * NutrientWeight)`
    * **Limitation:** The score does *not* account for positive nutrients like fiber, protein, vitamins, or minerals. It is purely an indicator of nutrients to be mindful of.

---

## Installation and Execution

Follow these steps to run the application on a clean machine.

### 1. Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install dependencies:** (You will need to create this `requirements.txt` file from your environment)
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure API Key:**
    Create a file named `.env` in the root directory and add your Gemini API key:
    ```
    GEMINI_API_KEY="AIzaSy..."
    ```
    The application will automatically load this key.

### 2. Single Command to Run End-to-End

With the environment activated and configured, run the following command to start the web application:

```bash
streamlit run ui.py
This single command starts the web server, opens the application in your browser, and makes all functionality (camera scanning, analysis, etc.) available.
