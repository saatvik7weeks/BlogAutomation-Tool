import streamlit as st
import pandas as pd
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json

st.set_page_config(page_title="Blog Tools", layout="wide")

# Initialize OpenAI client from secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Sidebar
st.sidebar.title("Choose a Tool")
tool = st.sidebar.radio("Select", ["Blog Clustering Tool", "Blog Outline Tool","Keyword Research Tool", "Blog Generation Tool"])

# Google Sheets setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LVX21MqSo2QQp_TQpQIRRoPj5F-RxPMzAimsuCMl7oc/edit#gid=783600968"
SHEET_NAME = "Related Keywords"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ Load Google creds from Streamlit secrets
gcp_creds = json.loads(st.secrets["GOOGLE_SHEET_CREDS_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_creds, scope)
gc = gspread.authorize(creds)

N8N_WEBHOOK_URL = "https://natasha1.app.n8n.cloud/webhook/5d1ae903-739c-43e5-88a1-9f0caec3bcf7"


if tool == "Blog Clustering Tool":
    st.title("📊 Blog Clustering Tool")

    try:
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.worksheet(SHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        st.write("### Preview of Google Sheet Data", df.head())

        kd_col = "KD"
        vol_col = "MSV"

        df[kd_col] = pd.to_numeric(df[kd_col], errors="coerce")
        df[vol_col] = pd.to_numeric(df[vol_col], errors="coerce")
        df = df.dropna(subset=[kd_col, vol_col])
        df = df[(df[kd_col] >= 5) & (df[kd_col] <= 40)]
        df = df.sort_values(by=[vol_col, kd_col], ascending=[False, True])
        ranked_keywords = df[["Keyword", kd_col, vol_col]].to_dict(orient="records")

        if "selected" not in st.session_state:
            st.session_state.selected = []
        if "pointer" not in st.session_state:
            st.session_state.pointer = 0

        def fill_selection():
            while len(st.session_state.selected) < 5 and st.session_state.pointer < len(ranked_keywords):
                candidate = ranked_keywords[st.session_state.pointer]
                if candidate not in st.session_state.selected:
                    st.session_state.selected.append(candidate)
                st.session_state.pointer += 1

        fill_selection()

        st.subheader("Selected Keywords")
        for i, kw in enumerate(st.session_state.selected):
            col1, col2, col3, col4 = st.columns([3,1,1,1])
            col1.write(f"**{kw['Keyword']}**")
            col2.write(f"KD: {kw[kd_col]}")
            col3.write(f"Vol: {kw[vol_col]}")
            if col4.button("❌ Delete", key=f"del_{i}"):
                st.session_state.selected.pop(i)
                fill_selection()
                st.rerun()

    except Exception as e:
        st.error(f"⚠️ Error reading Google Sheet: {e}")

elif tool == "Blog Outline Tool":
    st.title("📝 Blog Outline Generator")

    blog_title = st.text_input("Enter Blog Title")
    keywords = st.text_area("Enter Target Keywords (comma or line separated)")

    if st.button("Generate Outline") and blog_title and keywords:
        prompt = f"""
        You are an expert blog strategist trained in Generative Engine Optimization (GEO) and AI-assisted content planning.
        Generate a structured blog outline with H2 and H3 headings based on:

        ✍️ Blog Title:
        {blog_title}

        🔑 Target Keywords:
        {keywords}

        Follow these rules:
        - Logical intro → H2 sections → conclusion
        - 4–6 H2s, each with 2–3 H3s
        - Use facts, stats, brand mentions, E-E-A-T signals
        - Add a 'People Also Ask' section with FAQs
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        st.session_state.outline = response.choices[0].message.content
        st.subheader("📑 Generated Blog Outline")
        st.markdown(st.session_state.outline)

        meta_prompt = f"""
        You're an SEO expert. Write 3 meta descriptions (120–155 characters) for the blog titled:
        "{blog_title}"

        Requirements:
        • Clear and compelling
        • Use relevant keywords naturally
        • Highlight value/benefit
        • Use action verbs to encourage clicks
        """

        meta_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.7
        )
        st.subheader("🔎 Suggested Meta Descriptions")
        st.markdown(meta_response.choices[0].message.content)

    if "outline" in st.session_state:
        st.subheader("💬 Edit Your Outline with AI Support")
        user_edit = st.text_input("Ask me to modify the outline (e.g., 'Change H2 X to Y')")
        if st.button("Update Outline") and user_edit:
            edit_prompt = f"""
            Here is the current blog outline:

            {st.session_state.outline}

            Instruction:
            {user_edit}

            Update the outline accordingly while keeping the structure intact.
            """
            edit_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": edit_prompt}],
                temperature=0.3
            )
            st.session_state.outline = edit_response.choices[0].message.content
            st.success("✅ Outline updated successfully!")
            st.markdown(st.session_state.outline)
            
elif tool == "Keyword Research Tool":
    st.title("🌍 Keyword Research Tool (via n8n)")

    keyword = st.text_input("Enter Keyword")
    country = st.text_input("Enter Country Name")

    if st.button("Submit to Workflow"):
        payload = {
            "keyword": keyword,
            "country": country
        }

        try:
            response = requests.post(
                "https://natasha1.app.n8n.cloud/webhook/5d1ae903-739c-43e5-88a1-9f0caec3bcf7",
                json=payload,
                timeout=20
            )
            if response.status_code == 200:
                st.success("✅ Data sent successfully to n8n workflow")
                try:
                    st.json(response.json())
                except:
                    st.write(response.text)
            else:
                st.error(f"❌ Failed with status {response.status_code}: {response.text}")

        except Exception as e:
            st.error(f"⚠️ Error sending request: {e}")



elif tool == "Blog Generation Tool":
    st.title("📝 Universal AI Blog Generator (1800–2000 Words)")

    blog_title = st.text_input("Blog Title")
    company_name = st.text_input("Company/Brand Name")
    target_audience = st.text_input("Target Audience")
    outline = st.text_area("Blog Outline (Use H2/H3 headings)")
    important_keywords = st.text_area("Important Keywords (repeat 5–6 times)")
    normal_keywords = st.text_area("Normal Keywords (repeat 1–2 times)")

    base_prompt = f"""
    You are an expert content writing assistant trained in Generative Engine Optimization (GEO) best practices. 
    Your goal is to create compelling and high-performing content for AI-powered search engines and generative AI tools. 
    Please use the following input to create a well-structured, authoritative, and engaging blog post. 
    Ensure that the content is valuable for both humans and AI tools, and follows all GEO Writing Rules as outlined.

    Input Data:
    Blog Title: “{blog_title}”
    Company/Brand Name: “{company_name}”
    Target Audience: “{target_audience}”
    Blog Outline: {outline}
    Important Keywords: {important_keywords}
    Normal Keywords (must all be included at least once): {normal_keywords}

    GEO Writing Rules:
    - Authority & Credibility: Naturally mention the provided company/brand name in the body text and metadata. 
      Use authoritative sources when mentioning statistics or facts. 
      Include examples and case studies to demonstrate expertise. 
      Reference current industry trends and developments where relevant.

    - Structure & Readability: 
      Follow the para-point-para format throughout the entire blog. 
      Use H2 and H3 headings exactly as outlined, with each heading having 5+ words. 
      Ensure the blog content is between 1500 to 1600 words (strictly enforced). 
      Keep paragraphs short (2–4 lines, 120–175 words). 
      Ensure each H3 section is within 150–160 words. 
      Write in active voice. 
      Include some question-style headings when natural.

    - Local & Contextual Relevance: 
      Mention physical locations, local services, or regional considerations if applicable. 
      Reference current industry trends and developments. 
      Use location-aware language where relevant.

    - Keyword Integration: 
      Important keywords must repeat 5–6 times across the blog. 
      Every normal keyword MUST appear at least once in the blog. 
      Use keywords contextually and naturally. 
      Include related terms and synonyms naturally.

    - Beginner-Friendly Approach: 
      Use a conversational tone. 
      Provide practical examples and real-world scenarios. 
      Break down complex ideas into digestible parts. 
      Follow the para-point-para format throughout the blog:
        * Start with a paragraph introducing a concept or idea.
        * Follow with a bullet-point list that elaborates or provides additional details.
        * Conclude with a paragraph summarizing the points or providing a closing thought.

    Output Requirements:
    - Follow the provided outline structure exactly without altering formatting. 
    - Keep the total word count between 1500 to 1600 words. 
    - Naturally incorporate all important and normal keywords. 
    - Add authoritative signals throughout the content. 
    - Keep the language accessible while maintaining expertise.
    """

    if st.button("Generate Blog"):
        with st.spinner("Generating blog, please wait..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": base_prompt}],
                    temperature=0.7,
                    max_tokens=4000
                )
                blog_content = response.choices[0].message.content
                st.subheader("📄 Generated Blog")
                st.write(blog_content)
                st.download_button("Download Blog as TXT", blog_content, "generated_blog.txt")
            except Exception as e:
                st.error(f"Error: {e}")
