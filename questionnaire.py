# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import requests

st.set_page_config(page_title="แบบประเมินสุขภาพนักศึกษาชั้นปีที่ 1", layout="wide")

BKK = ZoneInfo("Asia/Bangkok")

st.title("แบบประเมินสุขภาพพื้นฐานนักศึกษาชั้นปีที่ 1")
st.caption("ใช้กรอกระหว่างรอตรวจร่างกาย: ข้อมูลทั่วไป สุขภาพจิต พฤติกรรมสุขภาพ และสัญญาณชีพ")

# ---------- Helper ----------
def bmi_category(bmi):
    if bmi < 18.5:
        return "น้ำหนักน้อย"
    elif bmi < 23:
        return "ปกติ"
    elif bmi < 25:
        return "น้ำหนักเกิน"
    elif bmi < 30:
        return "อ้วนระดับ 1"
    else:
        return "อ้วนระดับ 2"

def phq2_score(q1, q2):
    mapping = {
        "ไม่มีเลย": 0,
        "เป็นบางวัน": 1,
        "เป็นมากกว่าครึ่งหนึ่งของวัน": 2,
        "เป็นเกือบทุกวัน": 3,
    }
    return mapping[q1] + mapping[q2]

def gad2_score(q1, q2):
    mapping = {
        "ไม่มีเลย": 0,
        "เป็นบางวัน": 1,
        "เป็นมากกว่าครึ่งหนึ่งของวัน": 2,
        "เป็นเกือบทุกวัน": 3,
    }
    return mapping[q1] + mapping[q2]

def traffic_color(label, level):
    if level == "green":
        st.success(label)
    elif level == "yellow":
        st.warning(label)
    else:
        st.error(label)

def save_to_github_csv(df_new):
    """
    Optional GitHub CSV persistence.
    Add these secrets in Streamlit Cloud:
    GITHUB_TOKEN="..."
    GITHUB_REPO="username/repo"
    GITHUB_BRANCH="main"
    GITHUB_FILE_PATH="first_year_health.csv"
    """
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        path = st.secrets.get("GITHUB_FILE_PATH", "first_year_health.csv")
    except Exception:
        return False, "ยังไม่ได้ตั้งค่า GitHub secrets"

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    r = requests.get(url, headers=headers, params={"ref": branch})

    if r.status_code == 200:
        file_info = r.json()
        sha = file_info["sha"]
        old_content = base64.b64decode(file_info["content"]).decode("utf-8")
        df_old = pd.read_csv(pd.io.common.StringIO(old_content))
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    elif r.status_code == 404:
        sha = None
        df_all = df_new
    else:
        return False, f"GitHub read error: {r.status_code} {r.text}"

    csv_text = df_all.to_csv(index=False)
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"update first year health data {datetime.now(BKK).isoformat()}",
        "content": encoded,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    put = requests.put(url, headers=headers, json=payload)

    if put.status_code in [200, 201]:
        return True, "บันทึกเข้า GitHub CSV สำเร็จ"
    return False, f"GitHub write error: {put.status_code} {put.text}"

# ---------- Form ----------
with st.form("student_health_form"):
    st.header("1) ข้อมูลทั่วไป")
    c1, c2, c3 = st.columns(3)
    with c1:
        student_code = st.text_input("รหัสนักศึกษา / รหัสประจำตัว")
        faculty = st.selectbox("คณะ", ["", "วิศวกรรมศาสตร์", "วิทยาศาสตร์การกีฬา", "สัตวแพทยศาสตร์", "เกษตร", "ศิลปศาสตร์และวิทยาศาสตร์", "อื่น ๆ"])
    with c2:
        sex = st.selectbox("เพศ", ["", "ชาย", "หญิง", "ไม่ระบุ"])
        age = st.number_input("อายุ", 15, 40, 18)
    with c3:
        tel = st.text_input("เบอร์โทรศัพท์")
        concern = st.text_area("เรื่องสุขภาพที่กังวลมากที่สุด", height=80)

    st.header("2) วัดร่างกายและสัญญาณชีพด้วยตนเอง")
    c1, c2, c3 = st.columns(3)
    with c1:
        bw = st.number_input("น้ำหนัก BW (kg)", 20.0, 200.0, 60.0, 0.1)
        ht = st.number_input("ส่วนสูง Ht (cm)", 100.0, 220.0, 165.0, 0.1)
        bmi = bw / ((ht / 100) ** 2)
        st.metric("BMI", f"{bmi:.1f}", bmi_category(bmi))
    with c2:
        sbp = st.number_input("ความดันตัวบน SBP (mmHg)", 60, 250, 120)
        dbp = st.number_input("ความดันตัวล่าง DBP (mmHg)", 30, 160, 80)
        pulse = st.number_input("ชีพจร P (ครั้ง/นาที)", 30, 200, 80)
    with c3:
        temp = st.number_input("อุณหภูมิ T (°C)", 34.0, 42.0, 36.8, 0.1)
        rr = st.number_input("อัตราหายใจ RR (ครั้ง/นาที)", 6, 50, 18)
        spo2 = st.number_input("SpO₂ (%)", 70, 100, 98)

    st.header("3) แบบคัดกรองสุขภาพจิตแบบสั้น")
    st.subheader("PHQ-2: อารมณ์ซึมเศร้าในช่วง 2 สัปดาห์ที่ผ่านมา")
    phq1 = st.radio("เบื่อ ไม่สนใจ หรือไม่เพลิดเพลินกับสิ่งต่าง ๆ", ["ไม่มีเลย", "เป็นบางวัน", "เป็นมากกว่าครึ่งหนึ่งของวัน", "เป็นเกือบทุกวัน"])
    phq2 = st.radio("รู้สึกไม่สบายใจ ซึมเศร้า หรือสิ้นหวัง", ["ไม่มีเลย", "เป็นบางวัน", "เป็นมากกว่าครึ่งหนึ่งของวัน", "เป็นเกือบทุกวัน"])

    st.subheader("GAD-2: ความกังวลในช่วง 2 สัปดาห์ที่ผ่านมา")
    gad1 = st.radio("รู้สึกกังวล กระวนกระวาย หรือเครียดมาก", ["ไม่มีเลย", "เป็นบางวัน", "เป็นมากกว่าครึ่งหนึ่งของวัน", "เป็นเกือบทุกวัน"])
    gad2 = st.radio("ไม่สามารถหยุดหรือควบคุมความกังวลได้", ["ไม่มีเลย", "เป็นบางวัน", "เป็นมากกว่าครึ่งหนึ่งของวัน", "เป็นเกือบทุกวัน"])

    stress = st.slider("ระดับความเครียดโดยรวมวันนี้ 0–10", 0, 10, 3)
    fatigue = st.slider("ระดับความเหนื่อยล้า/อ่อนเพลียวันนี้ 0–10", 0, 10, 3)
    sleep_quality = st.selectbox("คุณภาพการนอนช่วง 2 สัปดาห์ที่ผ่านมา", ["ดีมาก", "ดี", "ปานกลาง", "ไม่ค่อยดี", "แย่มาก"])

    st.header("4) พฤติกรรมสุขภาพและความปลอดภัย")
    c1, c2 = st.columns(2)
    with c1:
        exercise = st.selectbox("ความถี่ออกกำลังกาย", ["ไม่ออกเลย", "1–2 วัน/สัปดาห์", "3–4 วัน/สัปดาห์", "≥5 วัน/สัปดาห์"])
        breakfast = st.selectbox("การรับประทานอาหารเช้า", ["ทุกวัน", "4–6 วัน/สัปดาห์", "1–3 วัน/สัปดาห์", "ไม่ค่อยรับประทาน"])
        sweet_drink = st.selectbox("เครื่องดื่มหวาน", ["ไม่ดื่ม", "1–2 ครั้ง/สัปดาห์", "3–5 ครั้ง/สัปดาห์", "ทุกวัน"])
    with c2:
        transport = st.selectbox("วิธีเดินทางหลัก", ["เดิน", "จักรยาน", "รถจักรยานยนต์", "รถยนต์", "รถโดยสาร/รถสาธารณะ", "อื่น ๆ"])
        helmet = st.selectbox("ถ้าใช้รถจักรยานยนต์: สวมหมวกกันน็อค", ["ไม่เกี่ยวข้อง", "ทุกครั้ง", "เกือบทุกครั้ง", "บางครั้ง", "น้อยมาก", "ไม่เคย"])
        near_miss = st.selectbox("เคยเกือบเกิดอุบัติเหตุใน 6 เดือนที่ผ่านมา", ["ไม่เคย", "1 ครั้ง", "2–3 ครั้ง", ">3 ครั้ง"])

    risky = st.multiselect(
        "พฤติกรรมเสี่ยงขณะเดินทาง/ขับขี่",
        ["ขับเร็ว", "ฝ่าไฟแดง", "ขับย้อนศร", "ขับขณะง่วง", "ใช้โทรศัพท์ขณะขับขี่", "ดื่มแอลกอฮอล์ก่อนขับขี่", "ไม่พบพฤติกรรมเสี่ยง"],
        default=["ไม่พบพฤติกรรมเสี่ยง"]
    )

    consent = st.checkbox("ข้าพเจ้ายินยอมให้ใช้ข้อมูลเพื่อการตรวจสุขภาพและวิเคราะห์ภาพรวมโดยไม่เปิดเผยตัวตน")
    submitted = st.form_submit_button("บันทึกข้อมูล")

# ---------- Result ----------
if submitted:
    if not consent:
        st.error("กรุณากดยินยอมก่อนบันทึกข้อมูล")
        st.stop()

    phq_score = phq2_score(phq1, phq2)
    gad_score = gad2_score(gad1, gad2)

    bp_flag = "green"
    if sbp >= 140 or dbp >= 90 or sbp < 90:
        bp_flag = "red"
    elif sbp >= 130 or dbp >= 80:
        bp_flag = "yellow"

    mental_flag = "green"
    if phq_score >= 3 or gad_score >= 3 or stress >= 8:
        mental_flag = "red"
    elif stress >= 5 or fatigue >= 7 or sleep_quality in ["ไม่ค่อยดี", "แย่มาก"]:
        mental_flag = "yellow"

    safety_flag = "green"
    if "ดื่มแอลกอฮอล์ก่อนขับขี่" in risky or helmet in ["น้อยมาก", "ไม่เคย"] or near_miss in ["2–3 ครั้ง", ">3 ครั้ง"]:
        safety_flag = "red"
    elif "ใช้โทรศัพท์ขณะขับขี่" in risky or near_miss == "1 ครั้ง" or helmet == "บางครั้ง":
        safety_flag = "yellow"

    st.header("สรุปผลเบื้องต้น")
    c1, c2, c3 = st.columns(3)
    with c1:
        traffic_color(f"ร่างกาย/BP: {bp_flag.upper()}", bp_flag)
    with c2:
        traffic_color(f"สุขภาพจิต: {mental_flag.upper()}", mental_flag)
    with c3:
        traffic_color(f"ความปลอดภัยการเดินทาง: {safety_flag.upper()}", safety_flag)

    st.info("หมายเหตุ: ผลนี้เป็นการคัดกรองเบื้องต้น ไม่ใช่การวินิจฉัย กรุณาพบแพทย์/พยาบาลเพื่อตรวจยืนยัน")

    record = {
        "timestamp_bkk": datetime.now(BKK).strftime("%Y-%m-%d %H:%M:%S"),
        "student_code": student_code,
        "faculty": faculty,
        "sex": sex,
        "age": age,
        "tel": tel,
        "concern": concern,
        "bw_kg": bw,
        "ht_cm": ht,
        "bmi": round(bmi, 1),
        "bmi_category": bmi_category(bmi),
        "sbp": sbp,
        "dbp": dbp,
        "pulse": pulse,
        "temp_c": temp,
        "rr": rr,
        "spo2": spo2,
        "phq2_score": phq_score,
        "gad2_score": gad_score,
        "stress_0_10": stress,
        "fatigue_0_10": fatigue,
        "sleep_quality": sleep_quality,
        "exercise": exercise,
        "breakfast": breakfast,
        "sweet_drink": sweet_drink,
        "transport": transport,
        "helmet": helmet,
        "near_miss": near_miss,
        "risky_behavior": ", ".join(risky),
        "bp_flag": bp_flag,
        "mental_flag": mental_flag,
        "safety_flag": safety_flag,
    }

    df = pd.DataFrame([record])
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "ดาวน์โหลด CSV รายบุคคล",
        data=csv,
        file_name=f"first_year_health_{student_code or 'student'}.csv",
        mime="text/csv",
    )

    ok, msg = save_to_github_csv(df)
    if ok:
        st.success(msg)
    else:
        st.warning(f"ยังไม่บันทึกเข้า GitHub: {msg}")