import streamlit as st
import cv2
import requests
import json
from PIL import Image
from pyzbar.pyzbar import decode
import time
import numpy as np
import re

# --- API KEY CONFIGURATION ---
st.sidebar.header("API Configuration")
st.sidebar.markdown("To get your own API key, visit [Google AI Studio](https://aistudio.google.com/app/apikey).")
gemini_api_key_input = st.sidebar.text_input(
    "Enter your Gemini API Key", type="password", help="Your key is not stored."
)

genai = None
if gemini_api_key_input:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key_input)
    except ImportError:
        st.error("The `google-generativeai` package is not installed. Please run `pip install google-generativeai`.")
    except Exception as e:
        st.error(f"An error occurred during API configuration: {e}")

# =============== BACKEND LOGIC (FROM YOUR NOTEBOOK) ===============

def fetch_openfoodfacts_nutrition(barcode):
    """Fetches nutritional information from the OpenFoodFacts API."""
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("status") == 1 and "product" in data:
            product = data["product"]
            nutriments = product.get("nutriments", {})
            nutrition_info = {
                "Calories (kcal)": nutriments.get("energy-kcal_100g"),
                "Fat (g)": nutriments.get("fat_100g"),
                "Saturated Fat (g)": nutriments.get("saturated-fat_100g"),
                "Carbohydrates (g)": nutriments.get("carbohydrates_100g"),
                "Sugars (g)": nutriments.get("sugars_100g"),
                "Protein (g)": nutriments.get("proteins_100g"),
                "Salt (g)": nutriments.get("salt_100g"),
                "Sodium (mg)": nutriments.get("sodium_100g", 0) * 1000,
            }
            nutrition_info = {k: v for k, v in nutrition_info.items() if v is not None}
            return {
                "source": "OpenFoodFacts",
                "barcode": barcode,
                "name": product.get("product_name", "Unknown Product"),
                "ingredients": product.get("ingredients_text_en", "Not specified"),
                "nutrition_per_100g": nutrition_info,
            }
        return None
    except requests.RequestException as e:
        st.warning(f"OpenFoodFacts API error: {e}")
        return None

def scan_barcode_streamlit():
    """Opens a camera feed within Streamlit to scan for a barcode."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("Error: Could not open camera.")
        return None
    
    barcode = None
    info_placeholder = st.empty()
    image_placeholder = st.empty()
    
    info_placeholder.info("👉 Point camera at a barcode...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        decoded_objects = decode(Image.fromarray(frame))
        if decoded_objects:
            barcode_obj = decoded_objects[0]
            barcode = barcode_obj.data.decode("utf-8")
            
            points = barcode_obj.polygon
            if len(points) == 4:
                pts = np.array([(p.x, p.y) for p in points], dtype=np.int32)
                cv2.polylines(frame_rgb, [pts], True, (0, 255, 0), 3)
            
            cv2.putText(frame_rgb, f"Detected: {barcode}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            # --- FIX APPLIED HERE ---
            image_placeholder.image(frame_rgb, caption='Scanning...', use_container_width=True)
            info_placeholder.success(f"✅ Barcode Detected: {barcode}")
            time.sleep(2)
            break

        # --- AND FIX APPLIED HERE ---
        image_placeholder.image(frame_rgb, caption='Scanning...', use_container_width=True)
        
    cap.release()
    cv2.destroyAllWindows()
    info_placeholder.empty()
    image_placeholder.empty()
    return barcode

def load_rules(path="scoring_rules.json"):
    """Loads scoring rules from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)

def normalize_product_data(data):
    """Normalizes product data to a consistent format for scoring."""
    nutrition = data.get("nutrition_per_100g", {})
    mapping = {
        "sugars": ["Sugars (g)", "sugars"],
        "saturates": ["Saturated Fat (g)", "saturates"],
        "salt": ["Salt (g)", "salt"],
        "fat": ["Fat (g)", "fat"],
    }
    normalized = {}
    for key, variants in mapping.items():
        for v in variants:
            if v in nutrition and nutrition[v] is not None:
                try:
                    normalized[key] = float(nutrition[v])
                    break
                except (ValueError, TypeError):
                    continue
        if key not in normalized:
            normalized[key] = 0.0
    return {
        "name": data.get("name", "Unknown"),
        "barcode": data.get("barcode", ""),
        "nutrition": normalized,
    }

def classify_value(value, thresholds):
    """Classifies a nutrient value into a color band using simple logic."""
    for band, expr in thresholds.items():
        try:
            if "and" in expr:
                parts = expr.split(" and ")
                lower_bound = float(re.findall(r"[\d\.]+", parts[0])[0])
                upper_bound = float(re.findall(r"[\d\.]+", parts[1])[0])
                if lower_bound < value <= upper_bound:
                    return band
            else:
                bound = float(re.findall(r"[\d\.]+", expr)[0])
                if "<=" in expr and value <= bound:
                    return band
                if ">" in expr and value > bound:
                    return band
        except (ValueError, IndexError):
            continue
    return "unknown"

def score_product(product, rules, product_type="food"):
    """Scores the product based on normalized nutrition data and rules."""
    nutrients = product["nutrition"]
    results = {}
    total_score = 0.0
    for n, val in nutrients.items():
        if n in rules["thresholds"][product_type]:
            thresholds = rules["thresholds"][product_type][n]
            band = classify_value(val, thresholds)
            subscore = rules["scores"].get(band, 0)
            weighted = subscore * rules["weights"].get(n, 0)
            results[n] = {
                "value_per_100g": val, "band": band,
                "subscore": subscore, "weighted_score": weighted,
            }
            total_score += weighted
    
    band_label = "Unknown"
    for _, info in rules["bands"].items():
        if info["min"] <= total_score <= info["max"]:
            band_label = info["label"]
            break
            
    return {
        "product": product["name"], "barcode": product["barcode"],
        "score": round(total_score, 1), "band": band_label,
        "results": results, "evidence_sources": rules["evidence_sources"],
    }

def ask_gemini_comment(scored):
    """Generates a consumer-friendly comment using the Gemini API."""
    if not genai:
        return "Gemini API not configured. Cannot generate comment."
    prompt = f"""
    You are a nutrition assistant.
    Product: {scored['product']}
    Score: {scored['score']} ({scored['band']}).
    Nutrient breakdown: {json.dumps(scored['results'], indent=2)}
    Please give a short, consumer-friendly comment (2–3 sentences) about this product’s healthiness based ONLY on the data provided.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could not generate comment: {e}"

# =============== STREAMLIT UI ===============

st.set_page_config(page_title="Food Product Scanner", layout="wide")
st.title("🍓 Food Product Health Scanner")
st.markdown("Scan a product's barcode to get an instant health analysis.")

if 'final_score' not in st.session_state:
    st.session_state.final_score = None

st.sidebar.header("Actions")
if st.sidebar.button("📷 Scan from Camera", type="primary"):
    st.session_state.final_score = None
    barcode = scan_barcode_streamlit()
    if barcode:
        with st.spinner(f"Analyzing barcode: {barcode}..."):
            data = fetch_openfoodfacts_nutrition(barcode)
            if data and data.get("nutrition_per_100g"):
                rules = load_rules()
                product = normalize_product_data(data)
                scored = score_product(product, rules)
                comment = ask_gemini_comment(scored)
                scored["llm_comment"] = comment
                scored["raw_data"] = data
                st.session_state.final_score = scored
            else:
                st.error("Could not retrieve nutritional information for this product.")
    else:
        st.warning("No barcode was detected.")

st.header("Analysis Results")

if st.session_state.final_score:
    score_data = st.session_state.final_score
    score_value = score_data['score']
    
    st.subheader(f"Health Score: {score_value}/100")
    if 70 <= score_value <= 100:
        color = "green"
    elif 30 <= score_value < 70:
        color = "orange"
    else:
        color = "red"
    
    st.markdown(f"""
        <div style="background-color: #eee; border-radius: 10px; padding: 3px;">
            <div style="background-color: {color}; width: {score_value}%; height: 25px; border-radius: 7px; text-align: center; color: white; font-weight: bold; line-height: 25px;">
                {score_value}
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"**Overall Rating: <span style='color:{color};'>{score_data['band']}</span>**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2,3])
    with col1:
        st.info(f"**Expert Comment:**\n\n{score_data['llm_comment']}")
    
    with col2:
        st.subheader("Nutrient Details (per 100g)")
        results = score_data['results']
        if results:
            metric_cols = st.columns(len(results))
            color_map = {"green": "🟢", "amber": "🟡", "red": "🔴"}
            for i, (nutrient, details) in enumerate(results.items()):
                with metric_cols[i]:
                    band_emoji = color_map.get(details['band'], "⚪️")
                    st.metric(
                        label=f"{band_emoji} {nutrient.capitalize()}",
                        value=f"{details['value_per_100g']}g"
                    )
    st.divider()

    with st.expander("Show Initial Scanned Data"):
        st.json(score_data['raw_data'])
    
    with st.expander("Authoritative Sources"):
        for source in score_data['evidence_sources']:
            st.markdown(f"- {source}")

else:
    st.info("Enter your Gemini API key in the sidebar and click 'Scan from Camera' to begin.")

