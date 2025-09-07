import streamlit as st
import cv2
import requests
import json
from PIL import Image
from pyzbar.pyzbar import decode
import time
import numpy as np
import re
import pandas as pd
import os

# --- API KEY CONFIGURATION ---
# Try multiple methods to get the API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyDyCpewLsgJvBkPGN2pFWzo3x_8a_-PP4c')

# Configure the Generative AI model
api_configured = False
genai = None

try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    # Test the configuration by listing models
    try:
        models = genai.list_models()
        api_configured = True
        print("Gemini API configured successfully")
    except Exception as e:
        print(f"Failed to verify Gemini API configuration: {e}")
        api_configured = False
except ImportError:
    st.error("The `google-generativeai` package is not installed. Please run `pip install google-generativeai`.")
    api_configured = False
except Exception as e:
    st.error(f"An error occurred during API configuration: {e}")
    api_configured = False

# =============== BACKEND LOGIC ===============

def fetch_openfoodfacts_nutrition(barcode):
    """Fetches nutritional information from the OpenFoodFacts API."""
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        # UPDATED: Increased timeout from 10 to 20 seconds for more reliability
        res = requests.get(url, timeout=20)
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
                "Sodium (mg)": nutriments.get("sodium_100g", 0) * 1000 if nutriments.get("sodium_100g") else None,
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
        decoded_objects = decode(Image.fromarray(frame_rgb))
        if decoded_objects:
            barcode = decoded_objects[0].data.decode("utf-8")
            points = decoded_objects[0].polygon
            if len(points) == 4:
                pts = np.array([(p.x, p.y) for p in points], dtype=np.int32)
                cv2.polylines(frame_rgb, [pts], True, (0, 255, 0), 3)
            cv2.putText(frame_rgb, f"Detected: {barcode}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            image_placeholder.image(frame_rgb, use_container_width=True)
            info_placeholder.success(f"✅ Barcode Detected: {barcode}")
            time.sleep(2)
            break
        image_placeholder.image(frame_rgb, use_container_width=True)

    cap.release()
    cv2.destroyAllWindows()
    info_placeholder.empty()
    image_placeholder.empty()
    return barcode

def load_rules(path="scoring_rules.json"):
    """Load scoring rules from JSON file."""
    if not os.path.exists(path):
        default_rules = {
            "reference_intakes": {
                "energy_kj": 8400, "energy_kcal": 2000, "fat": 70,
                "saturates": 20, "sugars": 90, "salt": 6
            },
            "thresholds": {
                "food": {
                    "fat": {"green": "<=3", "amber": ">3 and <=17.5", "red": ">17.5"},
                    "saturates": {"green": "<=1.5", "amber": ">1.5 and <=5", "red": ">5"},
                    "sugars": {"green": "<=5", "amber": ">5 and <=22.5", "red": ">22.5"},
                    "salt": {"green": "<=0.3", "amber": ">0.3 and <=1.5", "red": ">1.5"}
                },
                "drinks": {
                    "fat": {"green": "<=1.5", "amber": ">1.5 and <=8.75", "red": ">8.75"},
                    "saturates": {"green": "<=0.75", "amber": ">0.75 and <=2.5", "red": ">2.5"},
                    "sugars": {"green": "<=2.5", "amber": ">2.5 and <=11.25", "red": ">11.25"},
                    "salt": {"green": "<=0.3", "amber": ">0.3 and <=0.75", "red": ">0.75"}
                }
            },
            "weights": { "sugars": 0.40, "saturates": 0.25, "salt": 0.20, "fat": 0.15 },
            "scores": {"green": 100, "amber": 50, "red": 0},
            "bands": {
                "healthy": {"min": 70, "max": 100, "label": "Green Band", "description": "Healthy choice"},
                "moderate": {"min": 40, "max": 69, "label": "Amber Band", "description": "Moderate health profile"},
                "less_healthy": {"min": 0, "max": 39, "label": "Red Band", "description": "Less healthy choice"}
            },
            "evidence_sources": [
                "UK Government Front of Pack Nutrition Labelling Guidance (2016)",
                "EU Regulation No. 1169/2011, Annex XIII",
                "WHO recommendations on free sugars (<10% energy intake)"
            ]
        }
        with open(path, 'w') as f:
            json.dump(default_rules, f, indent=2)
        st.info(f"Created default scoring rules file: {path}")

    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        st.error(f"Error reading scoring rules from '{path}'. Please check the file format.")
        return None

def normalize_product_data(data):
    """Normalize product data for scoring."""
    nutrition = data.get("nutrition_per_100g", {})
    mapping = {
        "sugars": ["Sugars (g)"], "saturates": ["Saturated Fat (g)"],
        "salt": ["Salt (g)"], "fat": ["Fat (g)"]
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
        "name": data.get("name", "Unknown"), "barcode": data.get("barcode", ""),
        "nutrition": normalized
    }

def classify_value(value, thresholds):
    """Classify a nutrient value into a band based on thresholds."""
    for band, expr in thresholds.items():
        try:
            if "and" in expr:
                parts = expr.split(" and ")
                lower = float(re.findall(r"[\d\.]+", parts[0])[0])
                upper = float(re.findall(r"[\d\.]+", parts[1])[0])
                if lower < value <= upper:
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
    """Score a product based on nutritional rules."""
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
                "value_per_100g": val, "band": band, "subscore": subscore,
                "weighted_score": weighted
            }
            total_score += weighted

    band_label = "Unknown"
    for _, info in rules["bands"].items():
        if info["min"] <= total_score <= info["max"]:
            band_label = info["label"]
            break

    return {
        "product": product["name"], "barcode": product["barcode"],
        "score": round(total_score, 1), "band": band_label, "results": results,
        "evidence_sources": rules["evidence_sources"]
    }

def ask_gemini_rest_api(prompt):
    """Fallback method using direct REST API call to Gemini."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                if len(parts) > 0 and 'text' in parts[0]:
                    return parts[0]['text'].strip()
        return "Could not extract response from Gemini API"
    except requests.exceptions.RequestException as e:
        return f"REST API error: {str(e)}"
    except Exception as e:
        return f"Error processing response: {str(e)}"

def ask_gemini_comment(scored):
    """Generate a health comment using Gemini API."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        return "Gemini API key not configured. Please add your API key to generate health comments."

    prompt = f"""You are a nutrition assistant.
Product: {scored['product']}
Score: {scored['score']} ({scored['band']}).
Nutrient breakdown:
{json.dumps(scored['results'], indent=2)}

Please give a short, consumer-friendly comment (2-3 sentences) about this product's healthiness based ONLY on the data provided."""

    if api_configured and genai:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            st.warning(f"SDK method failed: {str(e)}, trying REST API...")
    
    return ask_gemini_rest_api(prompt)

# =============== STREAMLIT UI ===============

st.set_page_config(page_title="Food Product Scanner", layout="wide")
st.title("🍓 Food Product Health Scanner")
st.markdown("Scan a product's barcode to get an instant health analysis.")

with st.sidebar:
    st.header("System Status")
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_API_KEY_HERE":
        if api_configured:
            st.success("✅ Gemini API: Ready (SDK)")
        else:
            st.warning("⚠️ Gemini API: Ready (REST)")
    else:
        st.error("❌ Gemini API: Not configured")
    st.divider()
    st.header("Actions")

if 'final_score' not in st.session_state:
    st.session_state.final_score = None

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_API_KEY_HERE":
    if st.sidebar.button("📷 Scan from Camera", type="primary"):
        st.session_state.final_score = None
        barcode = scan_barcode_streamlit()
        if barcode:
            with st.spinner(f"Analyzing barcode: {barcode}..."):
                data = fetch_openfoodfacts_nutrition(barcode)
                if data and data.get("nutrition_per_100g"):
                    rules = load_rules()
                    if rules:
                        product = normalize_product_data(data)
                        scored = score_product(product, rules)
                        scored["llm_comment"] = ask_gemini_comment(scored)
                        scored["raw_data"] = data
                        st.session_state.final_score = scored
                    else:
                        st.error("Could not load scoring rules.")
                else:
                    st.error("Could not retrieve nutritional information for this product.")
        else:
            st.warning("No barcode was detected.")

    with st.sidebar.expander("Manual Input"):
        manual_barcode = st.text_input("Enter barcode:")
        if st.button("Analyze") and manual_barcode:
            st.session_state.final_score = None
            with st.spinner(f"Analyzing barcode: {manual_barcode}..."):
                data = fetch_openfoodfacts_nutrition(manual_barcode)
                if data and data.get("nutrition_per_100g"):
                    rules = load_rules()
                    if rules:
                        product = normalize_product_data(data)
                        scored = score_product(product, rules)
                        scored["llm_comment"] = ask_gemini_comment(scored)
                        scored["raw_data"] = data
                        st.session_state.final_score = scored
                else:
                    st.error("Could not retrieve nutritional information for this product.")
else:
    st.sidebar.error("Please add a valid Gemini API key to the code.")

st.header("Analysis Results")

if st.session_state.final_score:
    score_data = st.session_state.final_score
    score_value = score_data['score']
    
    st.subheader(f"📦 {score_data.get('raw_data', {}).get('name', 'Unknown Product')}")
    
    st.subheader(f"Health Score: {score_value}/100")
    color = "green" if 70 <= score_value <= 100 else "orange" if 40 <= score_value < 70 else "red"
    st.markdown(
        f'<div style="background-color: #eee; border-radius: 10px; padding: 3px;">'
        f'<div style="background-color: {color}; width: {score_value}%; height: 25px; '
        f'border-radius: 7px; text-align: center; color: white; font-weight: bold; '
        f'line-height: 25px;">{score_value}</div></div>',
        unsafe_allow_html=True
    )
    st.markdown(f"**Overall Rating: <span style='color:{color};'>{score_data['band']}</span>**", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 3])
    with col1:
        st.info(f"**Expert Comment:**\n\n{score_data['llm_comment']}")
    with col2:
        st.subheader("Key Nutrient Indicators")
        results = score_data['results']
        if results:
            metric_cols = st.columns(len(results))
            color_map = {"green": "🟢", "amber": "🟡", "red": "🔴", "unknown": "⚪"}
            for i, (nutrient, details) in enumerate(results.items()):
                with metric_cols[i]:
                    emoji = color_map.get(details['band'], "⚪")
                    st.metric(
                        label=f"{emoji} {nutrient.capitalize()}",
                        value=f"{details['value_per_100g']}g"
                    )
    
    st.divider()

    st.subheader("Nutritional Components (per 100g)")
    nutrition_dict = score_data.get('raw_data', {}).get('nutrition_per_100g', {})
    if nutrition_dict:
        df = pd.DataFrame(nutrition_dict.items(), columns=['Nutrient', 'Value'])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("No detailed nutritional data available.")

    ingredients = score_data.get('raw_data', {}).get('ingredients', '')
    if ingredients and ingredients != "Not specified":
        with st.expander("Ingredients"):
            st.write(ingredients)

    with st.expander("Authoritative Sources"):
        for source in score_data['evidence_sources']:
            st.markdown(f"- {source}")

else:
    st.info("Scan a product to see the analysis here. You can use the camera or enter a barcode manually in the sidebar.")
