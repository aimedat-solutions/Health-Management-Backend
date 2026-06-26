"""Curated healthcare conversation templates and data lists.

Each template is a dict with ``title`` and ``messages``. Messages are
``(role, content)`` pairs that alternate between ``user`` and ``assistant``.
"""

from typing import Any

# ── Medical conditions (used to vary conversation names) ────────────────

PATIENT_COMPLAINTS: list[str] = [
    "Persistent headache and eye strain",
    "Lower back pain after sitting for long hours",
    "Unexplained fatigue and low energy",
    "Recurring throat infection and cough",
    "Digestive issues and bloating",
    "Joint pain in knees and shoulders",
    "Anxiety and difficulty sleeping",
    "Skin rash and allergic reactions",
    "High blood pressure concerns",
    "Blood sugar levels fluctuating",
    "Dizziness and lightheadedness",
    "Shortness of breath during mild activity",
    "Numbness in hands and feet",
    "Frequent indigestion and acid reflux",
    "Muscle cramps and dehydration",
]

SYMPTOM_DETAILS: list[str] = [
    "It started about a week ago and seems to be getting worse.",
    "I have had this on and off for the past month.",
    "The pain is dull and constant, rated 4 out of 10.",
    "It gets worse after meals and in the mornings.",
    "I have tried over-the-counter medication but it only helps temporarily.",
    "My family has a history of similar issues.",
    "I noticed it after I started my new workout routine.",
    "It is affecting my sleep and daily work.",
    "I have attached my recent lab reports for reference.",
    "My medication seems to have stopped working effectively.",
]

DOCTOR_RESPONSES: list[str] = [
    "Thank you for the detailed history. Based on your symptoms, I recommend scheduling a follow-up with your primary care physician for a full evaluation. In the meantime, stay hydrated and monitor your symptoms.",
    "I understand this is concerning. Your symptoms appear to be consistent with a common viral infection. Rest, fluids, and over-the-counter paracetamol should help. Seek immediate care if symptoms worsen.",
    "Thank you for sharing your lab results. Your HbA1c indicates pre-diabetes. I recommend consulting an endocrinologist and starting a structured diet and exercise plan. I can help you with dietary recommendations.",
    "Your symptoms suggest a possible musculoskeletal strain. Apply ice for the first 48 hours, then switch to heat. Avoid heavy lifting and consider seeing a physiotherapist if the pain persists beyond a week.",
    "Elevated blood pressure readings are concerning. Please monitor it twice daily for a week and maintain a log. Reduce sodium intake, exercise regularly, and consult your doctor if it remains elevated.",
    "Your reports show mild vitamin D deficiency. I recommend 15-20 minutes of morning sunlight exposure daily and foods rich in vitamin D like fatty fish and fortified dairy. A supplement may be needed.",
    "The symptoms you describe could be stress-related. Practice deep breathing exercises, maintain a consistent sleep schedule, and try to identify triggers. If symptoms persist, please consult a mental health professional.",
    "Your digestive issues could be related to diet. Try keeping a food diary to identify trigger foods. Avoid spicy and oily foods, eat smaller meals, and stay upright for 2-3 hours after eating.",
    "Joint pain with morning stiffness lasting more than 30 minutes can indicate inflammatory arthritis. Please consult a rheumatologist. Gentle stretching and warm compresses may provide temporary relief.",
    "Your symptoms suggest mild dehydration and electrolyte imbalance. Increase your water intake and consider an oral rehydration solution. If dizziness persists, please get checked for anemia.",
]

# ── Diet-related conversation templates ─────────────────────────────────

DIET_QUESTIONS: list[str] = [
    "Can you suggest a balanced meal plan for diabetes management?",
    "What foods should I eat to lower my cholesterol naturally?",
    "I am trying to lose weight — can you recommend a diet plan?",
    "What are the best foods for managing high blood pressure?",
    "Can you suggest a high-protein vegetarian diet for muscle building?",
    "I have iron deficiency — what should I include in my meals?",
    "What should I eat before and after a workout?",
    "Can you recommend foods that help with digestion and bloating?",
    "I am pregnant — what nutrients should I focus on?",
    "What foods should I avoid if I have acid reflux?",
]

DIET_RESPONSES: list[str] = [
    "For diabetes management, focus on low-glycemic foods like whole grains, legumes, leafy greens, and lean protein. Avoid refined sugars and simple carbohydrates. Eat small, frequent meals.",
    "To lower cholesterol naturally, include oats, almonds, fatty fish, olive oil, and foods rich in soluble fiber like beans and apples. Reduce saturated fats and avoid trans fats entirely.",
    "A weight-loss diet should prioritize protein (eggs, lentils, tofu), fiber-rich vegetables, and complex carbohydrates. Aim for a 500-calorie deficit. Stay hydrated and avoid sugary beverages.",
    "For blood pressure management, follow the DASH diet: plenty of fruits, vegetables, whole grains, low-fat dairy, and lean protein. Limit sodium to less than 2300 mg per day.",
    "For a vegetarian high-protein diet, include paneer, tofu, lentils, chickpeas, quinoa, Greek yogurt, and nuts. Aim for 1.6-2.2 g of protein per kg of body weight if you are active.",
    "For iron deficiency, include spinach, lentils, fortified cereals, pumpkin seeds, and tofu. Pair with vitamin C-rich foods like citrus fruits to enhance absorption. Avoid tea or coffee with meals.",
    "Pre-workout: banana with peanut butter, or oatmeal with berries. Post-workout: protein shake, eggs, or Greek yogurt with fruit. Stay hydrated before, during, and after exercise.",
    "For digestion, include yogurt, ginger, peppermint, fennel seeds, and fiber-rich foods. Avoid carbonated drinks, fried foods, and large meals. Eat slowly and chew thoroughly.",
    "During pregnancy, prioritize folic acid (leafy greens), iron (spinach, lentils), calcium (dairy, fortified foods), omega-3 (flaxseeds, walnuts), and adequate protein. Stay hydrated.",
    "For acid reflux, avoid spicy foods, citrus, tomatoes, caffeine, chocolate, and fried foods. Eat smaller meals, avoid lying down after eating, and elevate your head while sleeping.",
]

# ── Exercise-related conversation templates ─────────────────────────────

EXERCISE_QUESTIONS: list[str] = [
    "What exercises are safe for someone with lower back pain?",
    "Can you suggest a beginner-friendly morning workout routine?",
    "How should I start running if I have never run before?",
    "What are the best exercises for improving posture?",
    "Can you recommend knee-friendly cardio options?",
    "How often should I do strength training per week?",
    "What stretches help with neck and shoulder tension?",
    "Can you suggest exercises for diabetes management?",
    "What is a good post-pregnancy exercise routine?",
    "How do I prevent muscle soreness after workouts?",
]

EXERCISE_RESPONSES: list[str] = [
    "For lower back pain, try gentle exercises like cat-cow stretches, pelvic tilts, and knee-to-chest stretches. Avoid heavy lifting and high-impact activities. Consider physical therapy.",
    "A great beginner morning routine: 5 minutes of stretching, 15 minutes of brisk walking or jogging, 10 minutes of bodyweight exercises (squats, push-ups, planks), and 5 minutes of cool-down.",
    "Start with a walk-run method: walk for 2 minutes, then jog for 1 minute. Repeat for 20 minutes, 3 times a week. Gradually increase jogging time. Invest in proper running shoes.",
    "For better posture, try wall angels, chin tucks, cat-cow stretches, and rows. Strengthen your core with planks. Set hourly reminders to check your posture while sitting.",
    "Knee-friendly cardio includes swimming, cycling, elliptical training, and walking. Avoid running on hard surfaces and high-impact jumping exercises. Strengthen your quadriceps for knee support.",
    "For general fitness, aim for 2-3 strength training sessions per week with at least 48 hours between sessions targeting the same muscle group. Focus on compound exercises.",
    "For neck and shoulder tension, try shoulder rolls, neck tilts, upper trapezius stretches, and doorway chest stretches. Take frequent breaks if you work at a desk.",
    "For diabetes management, combine aerobic exercise (brisk walking, cycling) with resistance training. Aim for 150 minutes of moderate activity per week. Monitor blood sugar before and after exercise.",
    "Post-pregnancy: start with pelvic floor exercises (Kegels), deep breathing, and gentle walking. After 6-8 weeks, add core rehabilitation exercises. Consult your doctor before starting.",
    "To prevent muscle soreness, warm up for 5-10 minutes before exercise, cool down with stretching afterward, stay hydrated, and gradually increase intensity. Foam rolling can also help.",
]

# ── Lab report conversation templates ──────────────────────────────────

LAB_REPORT_QUESTIONS: list[str] = [
    "I just got my blood test results — can you help me understand them?",
    "My HbA1c is 6.8 — what does this mean?",
    "My vitamin B12 levels are low — how concerned should I be?",
    "My LDL cholesterol is 160 — is this dangerous?",
    "What do high liver enzymes indicate?",
    "My thyroid TSH is 5.5 — do I need medication?",
    "Can you explain my complete blood count report?",
    "My uric acid is high — what dietary changes do I need?",
    "My fasting blood sugar is 110 — is this pre-diabetes?",
    "What does an elevated CRP level mean?",
]

LAB_REPORT_RESPONSES: list[str] = [
    "I would be happy to help you understand your reports. Please share the specific values and their reference ranges. In general, focus on your HbA1c, lipid profile, liver and kidney function markers.",
    "An HbA1c of 6.8% indicates diabetes. Normal is below 5.7%. Please consult an endocrinologist. In the meantime, focus on a low-glycemic diet, regular exercise, and blood sugar monitoring.",
    "Low vitamin B12 (below 200 pg/mL) can cause fatigue, numbness, and cognitive issues. Include B12-rich foods like eggs, dairy, and fortified cereals. Severe deficiency may require injections.",
    "LDL of 160 mg/dL is high (optimal is below 100). Increase soluble fiber, reduce saturated fats, exercise regularly, and consider medication if lifestyle changes are insufficient after 3 months.",
    "Elevated liver enzymes (AST/ALT) can indicate fatty liver, medication effects, or viral hepatitis. Reduce alcohol, avoid processed foods, exercise, and follow up with a hepatologist if persistently elevated.",
    "A TSH of 5.5 mIU/L indicates subclinical hypothyroidism. Many doctors treat if symptoms are present or TSH exceeds 10. Monitor thyroid function and discuss treatment with your doctor.",
    "Your CBC report shows hemoglobin, white blood cells, and platelets. Low hemoglobin suggests anemia. High WBC can indicate infection. Abnormal platelet counts need further evaluation.",
    "High uric acid (above 7.0 mg/dL) increases gout risk. Avoid red meat, organ meats, shellfish, and alcohol. Drink plenty of water, eat cherries, and maintain a healthy weight.",
    "A fasting blood sugar of 110 mg/dL is in the impaired fasting glucose range (pre-diabetes). Normal is below 100. Lifestyle changes now can prevent progression to diabetes.",
    "Elevated CRP indicates inflammation in the body. It can be due to infection, autoimmune conditions, or chronic inflammation. Further testing is needed to identify the underlying cause.",
]

# ── Conversation templates (full multi-message dialogs) ─────────────────

CONVERSATION_TEMPLATES: list[dict[str, Any]] = [
    {
        "title": "{patient_name}'s headache and eye strain concern",
        "messages": [
            ("user", "I have been having persistent headaches for the past week, especially after working on the computer. My eyes also feel strained and dry. Is this something to worry about?"),
            ("assistant", "I understand your concern. Headaches combined with eye strain are very common, especially with prolonged screen time. This sounds like digital eye strain or tension headaches. Here are some steps you can try:\n\n1. Follow the 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds.\n2. Adjust your screen brightness and position.\n3. Use lubricating eye drops if your eyes feel dry.\n4. Ensure proper lighting to reduce glare.\n\nIf headaches persist despite these measures, or if you experience vision changes, nausea, or severe pain, please consult an ophthalmologist or neurologist."),
            ("user", "Thank you. I will try the 20-20-20 rule. Should I get my eyes checked even if the headaches go away?"),
            ("assistant", "Yes, I recommend getting a comprehensive eye examination annually, especially if you spend significant time on screens. Regular check-ups can detect refractive errors, dry eye syndrome, and other conditions early. If your current prescription glasses are more than a year old, an update may help reduce strain."),
        ],
    },
    {
        "title": "{patient_name}'s dietary plan request",
        "messages": [
            ("user", DIET_QUESTIONS[0]),
            ("assistant", DIET_RESPONSES[0]),
            ("user", "That is very helpful. Can you give me a sample one-day meal plan?"),
            ("assistant", "Here is a sample diabetes-friendly meal plan:\n\nBreakfast: Vegetable omelette with 1 slice of whole-grain toast\nMid-morning: A handful of almonds and an apple\nLunch: Grilled chicken or paneer with quinoa and steamed broccoli\nAfternoon snack: Greek yogurt with berries\nDinner: Grilled fish or tofu with sauteed spinach and sweet potato\nBefore bed: Warm turmeric milk (unsweetened)\n\nRemember to stay hydrated with water throughout the day. Avoid sugary drinks and fruit juices."),
        ],
    },
    {
        "title": "Lower back pain relief guidance for {patient_name}",
        "messages": [
            ("user", "I work a desk job and have been experiencing lower back pain for about 2 weeks. It gets worse when I sit for long periods. What exercises can help?"),
            ("assistant", "Lower back pain from prolonged sitting is very common. Here are some gentle exercises that can help:\n\n1. Cat-Cow stretch: 10-15 reps\n2. Child's pose: hold for 30 seconds\n3. Pelvic tilts: 10-15 reps\n4. Knee-to-chest stretch: hold for 20 seconds each side\n\nAlso, ensure your workstation is ergonomically set up. Your screen should be at eye level, feet flat on the floor, and lower back supported. Take a 5-minute walk break every hour.\n\nIf the pain radiates down your leg, or if you experience numbness, please consult a healthcare provider."),
            ("user", "The stretches are helping a bit. Should I use a heating pad or ice pack?"),
            ("assistant", "For the first 48 hours, use an ice pack (15-20 minutes at a time) to reduce inflammation. After that, switch to a heating pad to relax tight muscles. Alternate between heat and ice if both feel beneficial. If the pain persists beyond 2-3 weeks despite these measures, please see a physiotherapist."),
        ],
    },
    {
        "title": "{patient_name}'s anxiety and sleep difficulties",
        "messages": [
            ("user", "I have been feeling anxious lately and struggling to fall asleep at night. My mind keeps racing with work-related thoughts. What can I do to relax?"),
            ("assistant", "I am sorry you are experiencing this. Anxiety and sleep difficulties often go hand in hand. Here is a comprehensive approach:\n\n1. Establish a wind-down routine 60 minutes before bed (no screens, dim lights).\n2. Practice diaphragmatic breathing: inhale for 4 seconds, hold for 4, exhale for 6.\n3. Try progressive muscle relaxation before sleep.\n4. Keep a worry journal — write down your thoughts before bed.\n5. Avoid caffeine after 2 PM and limit alcohol.\n\nIf these techniques do not improve your sleep within 2 weeks, please consider consulting a mental health professional."),
            ("user", "I tried the breathing exercises last night and fell asleep faster! But I woke up at 3 AM and could not go back to sleep. What should I do when that happens?"),
            ("assistant", "Middle-of-the-night waking is very common with anxiety. If you wake up and cannot fall back asleep within 20 minutes:\n\n1. Get out of bed and go to another room.\n2. Read a physical book under dim light (no phones or tablets).\n3. Drink a small amount of warm water or chamomile tea.\n4. Return to bed only when you feel sleepy again.\n\nThis technique, called stimulus control, helps your brain associate the bed only with sleep. Consistency is key — it may take a week or two to see improvement."),
        ],
    },
    {
        "title": "Lab report review for {patient_name}",
        "messages": [
            ("user", LAB_REPORT_QUESTIONS[1]),
            ("assistant", LAB_REPORT_RESPONSES[1]),
            ("user", "That is worrying. What lifestyle changes should I start making immediately?"),
            ("assistant", "Here are immediate lifestyle changes for managing diabetes:\n\n1. Diet: Eliminate sugary drinks, refined flour products, and processed foods. Focus on whole grains, legumes, vegetables, and lean protein.\n2. Exercise: Walk for 30 minutes after meals. Aim for 150 minutes of moderate activity per week.\n3. Monitoring: Check your fasting and post-meal blood sugar regularly. Keep a log to share with your doctor.\n4. Hydration: Drink 8-10 glasses of water daily.\n5. Sleep: Prioritize 7-8 hours of quality sleep.\n\nPlease schedule an appointment with an endocrinologist for a comprehensive management plan."),
        ],
    },
    {
        "title": "Pregnancy nutrition advice for {patient_name}",
        "messages": [
            ("user", "I am 16 weeks pregnant and struggling with nausea. I am worried I am not getting enough nutrition for my baby. Any suggestions?"),
            ("assistant", "First trimester nausea is very common and usually improves by weeks 12-14. For you at 16 weeks, here are some nutrition strategies:\n\n1. Eat small, frequent meals every 2-3 hours.\n2. Keep dry crackers or toast by your bed and eat before getting up.\n3. Include ginger tea or lemon water for nausea relief.\n4. Focus on nutrient-dense foods when you can eat: eggs, yogurt, cooked vegetables.\n\nYour baby will take what it needs from your stores, so try not to worry. Do take your prenatal vitamins, especially folic acid and iron. If you cannot keep any food down for 24 hours, contact your OB-GYN."),
            ("user", "Thank you. The ginger tea is helping. What foods should I prioritize for the baby's brain development?"),
            ("assistant", "Great question! For your baby's brain development, focus on:\n\n1. Omega-3 fatty acids: flaxseeds, walnuts, chia seeds.\n2. Choline: eggs (especially the yolk), soybeans, peanuts.\n3. Iron: spinach, lentils, fortified cereals.\n4. Iodine: iodized salt, dairy, eggs.\n5. Folate: leafy greens, citrus fruits, beans.\n\nAim for a colorful plate with a variety of whole foods. Stay well-hydrated and continue your prenatal vitamins. You are doing a great job!"),
        ],
    },
    {
        "title": "{patient_name}'s medication side effect inquiry",
        "messages": [
            ("user", "I started taking metformin for my diabetes 2 weeks ago and I am experiencing digestive issues like bloating and diarrhea. Is this normal?"),
            ("assistant", "Yes, gastrointestinal side effects are very common when starting metformin. They often improve within 1-2 weeks as your body adjusts. Here are some tips:\n\n1. Take metformin with food (preferably with your largest meal).\n2. Ask your doctor about the extended-release version which is gentler.\n3. Avoid high-sugar and fatty foods that can worsen digestive symptoms.\n4. Stay hydrated to replace fluids lost from diarrhea.\n\nIf symptoms are severe, or if you experience vomiting, severe abdominal pain, or very rapid breathing, seek medical attention immediately as these could indicate lactic acidosis (rare but serious)."),
            ("user", "Should I stop taking it until I see my doctor?"),
            ("assistant", "Do NOT stop taking metformin without consulting your doctor first. Suddenly stopping diabetes medication can cause blood sugar levels to spike. Instead, call your doctor and explain your symptoms. They may adjust your dose, switch you to the extended-release version, or suggest taking it at a different time. Most patients find the side effects become manageable within a few weeks."),
        ],
    },
    {
        "title": "{patient_name}'s exercise and fitness query",
        "messages": [
            ("user", EXERCISE_QUESTIONS[1]),
            ("assistant", EXERCISE_RESPONSES[1]),
            ("user", "That sounds achievable. How soon can I expect to see results?"),
            ("assistant", "With consistency, you can expect:\n\n- Week 1-2: Improved mood and energy levels.\n- Week 3-4: Better stamina and easier morning wake-ups.\n- Week 6-8: Visible changes in muscle tone and endurance.\n- Week 10-12: Significant improvement in strength and overall fitness.\n\nThe key is consistency, not intensity. Listen to your body and gradually increase duration or intensity every 2 weeks. Take progress photos and measurements rather than relying only on the scale."),
        ],
    },
    {
        "title": "{patient_name}'s skin allergy concern",
        "messages": [
            ("user", "I developed a red, itchy rash on my arms and legs after using a new body lotion. It has been 3 days and is spreading. What should I do?"),
            ("assistant", "This sounds like allergic contact dermatitis from the new lotion. Here is what you should do:\n\n1. Immediately stop using the new lotion.\n2. Wash the affected areas with mild soap and cool water.\n3. Apply a hypoallergenic moisturizer to soothe the skin.\n4. Take an over-the-counter antihistamine like cetirizine.\n5. Apply calamine lotion or a 1% hydrocortisone cream for itching.\n\nIf the rash continues to spread despite stopping the product, or if you develop difficulty breathing, swelling of the face or lips, or blisters, seek immediate medical attention."),
            ("user", "I stopped using it but the rash is still spreading. Should I see a dermatologist?"),
            ("assistant", "Yes, if the rash is still spreading 3 days after discontinuing the product, please see a dermatologist. They can prescribe a stronger topical corticosteroid or oral medication. In the meantime, avoid hot showers, tight clothing, and scratching. Take photos of the rash daily to show the progression to your doctor."),
        ],
    },
    {
        "title": "{patient_name}'s blood pressure management",
        "messages": [
            ("user", "My blood pressure readings have been around 140/90 for the past week. I am 45 years old with no other health issues. Should I be worried?"),
            ("assistant", "A reading of 140/90 mmHg is classified as Stage 1 hypertension. While it is not an emergency, it should not be ignored. Here is a step-by-step plan:\n\n1. Confirm with proper measurement: rest for 5 minutes, feet flat on floor, arm at heart level. Measure at the same time each morning and evening.\n2. Lifestyle modifications:\n   - Reduce sodium intake (aim for less than 2,300 mg/day)\n   - Increase potassium-rich foods (bananas, sweet potatoes, spinach)\n   - Exercise 30 minutes daily, 5 days a week\n   - Limit alcohol and quit smoking if applicable\n   - Manage stress through meditation or deep breathing\n3. Schedule a doctor's appointment within 2 weeks.\n\nIf your readings exceed 180/120, seek emergency care."),
            ("user", "I will start the DASH diet and monitor regularly. At what point would I need medication?"),
            ("assistant", "Most doctors recommend lifestyle modifications for 3-6 months first. If your BP remains above 140/90 despite consistent lifestyle changes, medication is typically prescribed. Some factors that might lead to earlier medication include:\n\n- Family history of early heart disease\n- Presence of diabetes or kidney disease\n- BP consistently above 150/95\n\nThe goal is to keep BP below 130/80 for most adults. Work with your doctor who will tailor a plan specific to your health profile."),
        ],
    },
]

# ── Agent execution templates ──────────────────────────────────────────

AGENT_INPUT_TEMPLATES: list[dict[str, Any]] = [
    {
        "input": {"prompt": "Analyze patient symptoms and provide triage assessment", "urgency": "non_urgent"},
        "output": {"urgency": "non_urgent", "recommendation": "Self-care with over-the-counter medication. Follow up if symptoms persist beyond 5 days.", "category": "general"},
    },
    {
        "input": {"prompt": "Generate conversation summary", "max_length": 200},
        "output": {"summary": "Patient reported persistent headaches and eye strain. AI provided digital eye strain management advice. Patient was advised to follow 20-20-20 rule and schedule annual eye exam.", "key_points": ["digital eye strain", "20-20-20 rule", "annual eye exam"]},
    },
    {
        "input": {"prompt": "Analyze diet and provide meal recommendations", "diet_type": "diabetes_management"},
        "output": {"meal_plan": "Low-glycemic diet recommended", "restricted_foods": ["refined sugar", "white rice", "fruit juices"], "recommended_foods": ["whole grains", "legumes", "leafy greens"]},
    },
    {
        "input": {"prompt": "Analyze lab report values", "lab_type": "hbA1c", "value": 6.8},
        "output": {"interpretation": "HbA1c of 6.8% indicates diabetes", "severity": "moderate", "recommendation": "Consult endocrinologist within 2 weeks"},
    },
]

# ── Feedback comments ──────────────────────────────────────────────────

FEEDBACK_COMMENTS: list[str] = [
    "Very helpful and clear explanation.",
    "The advice really helped me feel better.",
    "Could you provide more specific medication names?",
    "The response was too general for my situation.",
    "Excellent and thorough answer. Thank you!",
    "I wish the response had included more dietary suggestions.",
    "This was accurate and reassuring.",
    "The information matched what my doctor later told me.",
    "A bit confusing — too many medical terms.",
    "Perfect! Exactly what I needed to know.",
    "The exercise recommendations were very practical.",
    "I appreciated the step-by-step guidance.",
    "Would be better with visual aids or diagrams.",
    "Very professional and detailed response.",
]

# ── Doctor review notes ────────────────────────────────────────────────

DOCTOR_REVIEW_NOTES: dict[str, list[str]] = {
    "approved": [
        "AI assessment was accurate and aligned with my clinical evaluation.",
        "Recommendations are appropriate. No changes needed.",
        "Correct diagnosis and treatment suggestions. Well done.",
        "Patient education provided was comprehensive and accurate.",
    ],
    "needs_revision": [
        "The response could be more specific about medication dosages.",
        "Please include warnings about when to seek emergency care.",
        "Add more context about alternative treatment options.",
        "The dietary advice needs to be customized for this patient's allergies.",
    ],
    "rejected": [
        "The assessment missed key symptoms of the underlying condition.",
        "Incorrect interpretation of lab values. Requires retraining.",
        "Recommendations contradicted standard clinical guidelines.",
        "Missing critical safety disclaimers for this medication.",
    ],
}

# ── Users data ─────────────────────────────────────────────────────────

PATIENT_FIRST_NAMES: list[str] = [
    "Rahul", "Priya", "Amit", "Deepa", "Vikram", "Ananya", "Suresh",
    "Neha", "Rajesh", "Meera", "Sanjay", "Kavita", "Arun", "Pooja",
    "Ravi", "Sunita", "Manoj", "Shweta", "Vivek", "Nandini",
]

PATIENT_LAST_NAMES: list[str] = [
    "Sharma", "Patel", "Verma", "Singh", "Reddy", "Nair", "Joshi",
    "Gupta", "Kumar", "Iyer", "Desai", "Menon", "Chopra", "Malhotra",
    "Saxena", "Rao", "Kapoor", "Agarwal", "Bhat", "Mehta",
]

DOCTOR_FIRST_NAMES: list[str] = [
    "Dr. Arjun", "Dr. Shalini", "Dr. Prakash", "Dr. Anjali", "Dr. Karthik",
    "Dr. Lakshmi", "Dr. Rohit", "Dr. Divya", "Dr. Amitabh", "Dr. Shreya",
]

DOCTOR_LAST_NAMES: list[str] = [
    "Krishnan", "Bose", "Chatterjee", "Mukherjee", "Pillai",
    "Sethi", "Thakur", "Rana", "Bajaj", "Srinivasan",
]
