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
