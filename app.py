import streamlit as st
import json
import re
from groq import Groq

# ══════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="StudyBuddy AI 📚",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

/* ── Header banner ── */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    color: white;
    text-align: center;
    margin-bottom: 1.5rem;
}
.hero h1 { margin: 0; font-size: 2rem; }
.hero p  { margin: 0.3rem 0 0; opacity: .85; font-size: 0.95rem; }

/* ── Flashcard grid ── */
.fc-card {
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.6rem;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
    transition: box-shadow .25s, border-color .25s;
}
.fc-card:hover { box-shadow: 0 6px 18px rgba(102,126,234,.18); border-color:#667eea; }
.fc-q  { font-weight: 700; color: #2d3748; margin-bottom: .5rem; }
.fc-divider { border-top: 2px solid #667eea; margin: .5rem 0; }

/* ── Answer feedback boxes ── */
.box-correct  { background:#c6f6d5; border-left:4px solid #38a169; padding:.7rem 1rem; border-radius:0 8px 8px 0; color:#276749; margin-top:.4rem; }
.box-wrong    { background:#fed7d7; border-left:4px solid #e53e3e; padding:.7rem 1rem; border-radius:0 8px 8px 0; color:#c53030; margin-top:.4rem; }
.box-explain  { background:#ebf8ff; border-left:4px solid #3182ce; padding:.7rem 1rem; border-radius:0 8px 8px 0; color:#2c5282; margin-top:.4rem; }

/* ── Score banner ── */
.score-banner {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 14px;
    padding: 1.4rem;
    text-align: center;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 1.2rem;
}

/* ── Primary button override ── */
div.stButton > button {
    background: linear-gradient(135deg,#667eea,#764ba2);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: opacity .2s;
}
div.stButton > button:hover { opacity: .88; }
</style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════
#  GROQ CLIENT
# ══════════════════════════════════════════════════════════════════
@st.cache_resource
def get_client() -> Groq:
    """Return a cached Groq client."""
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


# ══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS  (unchanged)
# ══════════════════════════════════════════════════════════════════
CHAT_SYSTEM = """
You are StudyBuddy AI — a friendly, patient, and encouraging study assistant for students of all ages.
You support ALL languages, with special focus on Bangla (বাংলা) and English.

━━ LANGUAGE RULE ━━
• Always detect and respond in the EXACT same language the student uses.
• If they write in Bangla, respond fully in Bangla.
• If they mix Bangla + English, mirror their mix.

━━ CORE DUTY: ERROR CHECKING ━━
Whenever a student shares text, an answer, explanation, or any study content, you MUST:
1. ✅ Acknowledge what they got RIGHT first (be specific and warm).
2. Scan carefully for ALL of the following errors:
   - [FACTUAL ERROR]     — wrong facts or data
   - [CONCEPT ERROR]     — misunderstood idea or principle
   - [GRAMMAR ERROR]     — language / writing mistake
   - [INCOMPLETE]        — missing key information
3. For EACH error found:
   • Label it clearly (e.g., ❌ [FACTUAL ERROR])
   • In simple language, explain WHAT is wrong and WHY
   • Give the CORRECT information
   • Add a 💡 memory tip or analogy so it sticks
4. If everything is correct, celebrate them warmly! 🎉

━━ TEACHING STYLE ━━
• Break complex ideas into bite-sized steps.
• Use bullet points and numbered lists where helpful.
• Occasionally suggest a study strategy related to what they're learning.
• Always end with ONE engaging follow-up question to deepen understanding.
""".strip()

FLASHCARD_SYSTEM = """
You are StudyBuddy AI. Your task is to generate flashcards from study text.

CRITICAL: Return ONLY a raw JSON array — zero extra text, zero markdown, zero code fences.

Card count based on word count:
• < 80 words   → 3–4 cards
• 80–250 words → 5–8 cards
• 250–600 words→ 8–13 cards
• 600+ words   → 13–20 cards

JSON format (strictly):
[
  {"front": "Concise question or key term", "back": "Complete but brief answer (1–3 sentences max)"},
  ...
]

Rules:
• Questions test UNDERSTANDING, not just memorisation
• Answers are short and memorable
• Detect and use the same language as the input (Bangla stays Bangla, etc.)
""".strip()

MCQ_SYSTEM = """
You are StudyBuddy AI. Your task is to create multiple-choice questions from study text.

CRITICAL: Return ONLY a raw JSON array — zero extra text, zero markdown, zero code fences.

Question count based on word count:
• < 80 words    → 3 questions
• 80–250 words  → 4–5 questions
• 250–600 words → 6–8 questions
• 600+ words    → 9–12 questions

JSON format (strictly):
[
  {
    "question": "Clear question text",
    "options": ["A) option one", "B) option two", "C) option three", "D) option four"],
    "correct": "A",
    "explanation": "One-sentence explanation of why this is correct"
  },
  ...
]

Rules:
• Exactly ONE correct answer per question
• Distractors should be plausible, not obviously wrong
• Vary easy/medium/hard difficulty
• Test understanding, not just rote recall
• Detect and use the same language as the input
""".strip()


# ══════════════════════════════════════════════════════════════════
#  CORE API HELPER  (replaces deepseek_call entirely)
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
#  CORE API HELPER
# ══════════════════════════════════════════════════════════════════
def groq_call(
    system: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Call Groq. Its API is OpenAI-compatible so this is nearly identical
    to the original DeepSeek version — just a different client + model name.
    """
    client = get_client()
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # swap to "mixtral-8x7b-32768" or "gemma2-9b-it" if you prefer
        messages=[{"role": "system", "content": system}] + messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


# ══════════════════════════════════════════════════════════════════
#  HELPERS  (unchanged)
# ══════════════════════════════════════════════════════════════════
def safe_parse_json(raw: str) -> list:
    """
    Robustly parse a JSON array from model output.
    Handles stray markdown code fences or surrounding text.
    """
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    start = cleaned.find("[")
    end   = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON array found in response.")
    return json.loads(cleaned[start:end])


def truncate_history(history: list, max_turns: int = 12) -> list:
    """Keep only the last N message pairs to stay within token limits."""
    if len(history) > max_turns * 2:
        return history[-(max_turns * 2):]
    return history


# ══════════════════════════════════════════════════════════════════
#  MODE 1 — CHAT & LEARN
# ══════════════════════════════════════════════════════════════════
def page_chat():
    st.subheader("💬 Chat & Learn")
    st.caption(
        "Ask any question, paste your answer/notes for error-checking, or just have a conversation. "
        "বাংলা বা যেকোনো ভাষায় লিখুন!"
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        avatar = "🧑‍🎓" if msg["role"] == "user" else "📚"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask me anything or paste your answer for correction… (বাংলায় লিখতে পারেন!)"
    )

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="📚"):
            with st.spinner("Thinking…"):
                msgs = truncate_history(
                    [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                )
                response = groq_call(CHAT_SYSTEM, msgs)   # ← was deepseek_call
            st.markdown(response)

        st.session_state.chat_history.append({"role": "assistant", "content": response})

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  MODE 2 — FLASHCARDS
# ══════════════════════════════════════════════════════════════════
def page_flashcards():
    st.subheader("🃏 Flashcard Generator")
    st.caption("Paste your notes → get instant flashcards → test yourself one by one!")

    if "flashcards" not in st.session_state:
        text = st.text_area(
            "Paste your study material:",
            height=220,
            placeholder="Paste notes, a chapter summary, or any text…\nবাংলায়ও লিখতে পারেন!",
        )
        if st.button("✨ Generate Flashcards"):
            if not text.strip():
                st.warning("Please paste some study material first!")
                return
            with st.spinner("Creating flashcards…"):
                try:
                    raw = groq_call(                      # ← was deepseek_call
                        FLASHCARD_SYSTEM,
                        [{"role": "user", "content": f"Create flashcards from this text:\n\n{text}"}],
                        temperature=0.45,
                    )
                    cards = safe_parse_json(raw)
                    st.session_state.flashcards = cards
                    st.session_state.fc_revealed = {}
                    st.rerun()
                except Exception as err:
                    st.error(f"Could not generate flashcards — try again. (Detail: {err})")
        return

    cards = st.session_state.flashcards
    if "fc_revealed" not in st.session_state:
        st.session_state.fc_revealed = {}

    st.success(f"✅ {len(cards)} flashcards ready!")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("👁️ Reveal All"):
            st.session_state.fc_revealed = {i: True for i in range(len(cards))}
            st.rerun()
    with c2:
        if st.button("🙈 Hide All"):
            st.session_state.fc_revealed = {}
            st.rerun()
    with c3:
        if st.button("🔄 Generate New Set"):
            del st.session_state.flashcards
            del st.session_state.fc_revealed
            st.rerun()

    st.markdown("---")

    for i in range(0, len(cards), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(cards):
                break
            card = cards[idx]
            with col:
                st.markdown(
                    f"""<div class="fc-card">
                        <div class="fc-q">❓ {card["front"]}</div>
                        <div class="fc-divider"></div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                revealed = st.session_state.fc_revealed.get(idx, False)
                if revealed:
                    st.success(f"💡 {card['back']}")
                    if st.button("🙈 Hide", key=f"hide_{idx}"):
                        st.session_state.fc_revealed[idx] = False
                        st.rerun()
                else:
                    if st.button("👁️ Show Answer", key=f"show_{idx}"):
                        st.session_state.fc_revealed[idx] = True
                        st.rerun()
                st.write("")


# ══════════════════════════════════════════════════════════════════
#  MODE 3 — MCQ QUIZ
# ══════════════════════════════════════════════════════════════════
def page_mcq():
    st.subheader("📝 MCQ Quiz Generator")
    st.caption("Paste study material → get auto-generated multiple-choice questions → check your score!")

    if "mcq_questions" not in st.session_state:
        text = st.text_area(
            "Paste your study material:",
            height=220,
            placeholder="Paste notes, a chapter summary, or any text…\nবাংলায়ও লিখতে পারেন!",
        )
        if st.button("📝 Generate Quiz"):
            if not text.strip():
                st.warning("Please paste some study material first!")
                return
            with st.spinner("Building your quiz…"):
                try:
                    raw = groq_call(                      # ← was deepseek_call
                        MCQ_SYSTEM,
                        [{"role": "user", "content": f"Create MCQ questions from this text:\n\n{text}"}],
                        temperature=0.55,
                    )
                    questions = safe_parse_json(raw)
                    st.session_state.mcq_questions  = questions
                    st.session_state.mcq_answers    = {}
                    st.session_state.mcq_submitted  = False
                    st.rerun()
                except Exception as err:
                    st.error(f"Could not generate quiz — try again. (Detail: {err})")
        return

    questions = st.session_state.mcq_questions

    if not st.session_state.get("mcq_submitted", False):
        st.info(f"📋 {len(questions)} questions — answer all then press Submit.")

        for i, q in enumerate(questions):
            st.markdown(f"**Q{i+1}. {q['question']}**")
            choice = st.radio(
                label=f"q{i}",
                options=q["options"],
                key=f"mcq_radio_{i}",
                label_visibility="collapsed",
            )
            st.session_state.mcq_answers[i] = choice[0]
            st.markdown("---")

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("✅ Submit Quiz"):
                st.session_state.mcq_submitted = True
                st.rerun()
        with col2:
            if st.button("🔄 New Quiz"):
                for k in ["mcq_questions", "mcq_answers", "mcq_submitted"]:
                    st.session_state.pop(k, None)
                st.rerun()
        return

    answers = st.session_state.mcq_answers
    score   = sum(1 for i, q in enumerate(questions) if answers.get(i) == q["correct"])
    total   = len(questions)
    pct     = score / total * 100

    if pct >= 80:
        emoji, msg = "🏆", "Excellent work!"
    elif pct >= 60:
        emoji, msg = "👍", "Good job — keep going!"
    else:
        emoji, msg = "📖", "Keep studying — you'll get there!"

    st.markdown(
        f'<div class="score-banner">{emoji} {score}/{total} ({pct:.0f}%) — {msg}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 📋 Answer Review")

    for i, q in enumerate(questions):
        user_ans    = answers.get(i, "?")
        correct_ans = q["correct"]
        is_correct  = user_ans == correct_ans

        icon = "✅" if is_correct else "❌"
        st.markdown(f"**{icon} Q{i+1}. {q['question']}**")

        for opt in q["options"]:
            letter = opt[0]
            if letter == correct_ans:
                st.markdown(f'<div class="box-correct">✅ {opt}</div>', unsafe_allow_html=True)
            elif letter == user_ans and not is_correct:
                st.markdown(f'<div class="box-wrong">❌ {opt} ← your answer</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"&nbsp;&nbsp;&nbsp;{opt}")

        if not is_correct:
            st.markdown(f'<div class="box-explain">💡 {q["explanation"]}</div>', unsafe_allow_html=True)

        st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Retry Same Quiz"):
            st.session_state.mcq_answers   = {}
            st.session_state.mcq_submitted = False
            st.rerun()
    with col2:
        if st.button("📝 New Quiz"):
            for k in ["mcq_questions", "mcq_answers", "mcq_submitted"]:
                st.session_state.pop(k, None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  APP SHELL  (unchanged)
# ══════════════════════════════════════════════════════════════════
def main():
    st.markdown(
        """
<div class="hero">
  <h1>📚 StudyBuddy AI</h1>
  <p>Your AI-powered study companion &nbsp;•&nbsp; বাংলাসহ যেকোনো ভাষায় সাহায্য করি</p>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## 🗂️ Study Modes")
        mode = st.radio(
            "Pick a mode:",
            ["💬 Chat & Learn", "🃏 Flashcards", "📝 MCQ Quiz"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown(
            """
**💬 Chat & Learn**
Ask anything, paste your answer for instant error-correction and explanation.

**🃏 Flashcards**
Paste notes → get tap-to-reveal flashcards, great for memorisation.

**📝 MCQ Quiz**
Paste notes → take a quiz → get a score with detailed explanations.
""".strip()
        )
        st.markdown("---")
        st.caption("Powered by Groq 🤖 | Built with Streamlit")

    if mode == "💬 Chat & Learn":
        page_chat()
    elif mode == "🃏 Flashcards":
        page_flashcards()
    else:
        page_mcq()


if __name__ == "__main__":
    main()