
import streamlit as st
import pandas as pd
import re
from itertools import combinations
from collections import Counter
import plotly.express as px

# 페이지 설정
st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.write("송탄고 급식 메뉴를 분석하여 함께 등장하는 메뉴의 연관 규칙을 찾아봅니다.")

# 데이터 주소
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


# 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")

    # 필요한 열 확인
    df = df[["날짜", "식사", "메뉴"]].dropna(subset=["메뉴"])

    # 괄호와 괄호 안의 내용 제거
    def clean_menu(menu):
        menu = str(menu)

        # 괄호가 중첩된 경우도 처리
        while re.search(r"\([^()]*\)", menu):
            menu = re.sub(r"\([^()]*\)", "", menu)

        return menu.strip()

    # 하루의 메뉴를 장바구니 하나로 구성
    baskets = []

    for menu_text in df["메뉴"]:
        menus = [
            clean_menu(menu).strip()
            for menu in str(menu_text).split("|")
        ]

        # 빈 메뉴 제거 및 같은 날 중복 메뉴 제거
        menus = sorted(set(menu for menu in menus if menu))

        baskets.append(menus)

    return df, baskets


df, baskets = load_data()


# 연관 규칙 분석
def analyze_rules(baskets):
    total_days = len(baskets)

    # 각 메뉴가 등장한 날짜 수
    menu_counts = Counter()

    # 함께 등장한 메뉴 쌍의 횟수
    pair_counts = Counter()

    for basket in baskets:
        menu_counts.update(basket)

        for pair in combinations(sorted(basket), 2):
            pair_counts[pair] += 1

    # 연관 규칙 생성
    rules = []

    for (menu_a, menu_b), count in pair_counts.items():

        # A -> B
        support = count / total_days
        confidence = count / menu_counts[menu_a]
        lift = confidence / (menu_counts[menu_b] / total_days)

        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence,
            "향상도": lift
        })

        # B -> A
        confidence_reverse = count / menu_counts[menu_b]
        lift_reverse = confidence_reverse / (
            menu_counts[menu_a] / total_days
        )

        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_reverse,
            "향상도": lift_reverse
        })

    result = pd.DataFrame(rules)

    return result, menu_counts, pair_counts


rules, menu_counts, pair_counts = analyze_rules(baskets)


# 상단 통계
total_days = len(baskets)
total_menus = len(menu_counts)
total_pairs = len(pair_counts)

st.markdown("---")

st.markdown(
    f"""
    **급식 일수:** {total_days}일　 |　
    **메뉴 종류 수:** {total_menus}개　 |　
    **함께 나온 적이 있는 메뉴 쌍의 수:** {total_pairs}개
    """
)

st.markdown("---")


# 정렬 기준 선택
st.subheader("🔍 메뉴 연관 규칙")

col1, col2 = st.columns([2, 1])

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택",
        ["전체"] + sorted(menu_counts.keys())
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도 순", "신뢰도 순", "동시 순"]
    )


# 메뉴 필터링
filtered_rules = rules.copy()

if selected_menu != "전체":
    filtered_rules = filtered_rules[
        (filtered_rules["조건"] == selected_menu) |
        (filtered_rules["결과"] == selected_menu)
    ]


# 정렬
sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

filtered_rules = filtered_rules.sort_values(
    by=sort_columns[sort_option],
    ascending=False
).reset_index(drop=True)


# 표 출력
st.write("### 📋 연관 규칙 분석 결과")

if len(filtered_rules) > 0:
    display_df = filtered_rules.copy()

    # 소수점 표시
    display_df["지지도"] = display_df["지지도"].round(4)
    display_df["신뢰도"] = display_df["신뢰도"].round(4)
    display_df["향상도"] = display_df["향상도"].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"현재 표시된 연관 규칙: {len(filtered_rules)}개"
    )

else:
    st.info("선택한 메뉴와 관련된 연관 규칙이 없습니다.")


# 향상도 상위 10개 그래프
st.markdown("---")
st.subheader("📊 향상도 TOP 10")

if len(filtered_rules) > 0:

    top10 = (
        filtered_rules
        .sort_values("향상도", ascending=False)
        .head(10)
        .copy()
    )

    # 규칙 이름 만들기
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 가로 막대그래프
    fig = px.bar(
        top10.sort_values("향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "연관 규칙"
        },
        title="향상도가 높은 연관 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside"
    )

    fig.update_layout(
        height=500,
        xaxis_title="향상도",
        yaxis_title="메뉴 연관 규칙",
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.info("그래프로 표시할 연관 규칙이 없습니다.")


# 분석 결과 해석
st.markdown("---")
st.subheader("💡 분석 결과 읽는 방법")

st.markdown("""
- **지지도:** 전체 급식 중 두 메뉴가 함께 나온 비율입니다.
- **신뢰도:** 조건 메뉴가 나온 날에 결과 메뉴도 나온 비율입니다.
- **향상도:** 두 메뉴의 연관성이 우연히 함께 등장하는 경우보다 얼마나 높은지를 나타냅니다.

**향상도 해석**
- 1보다 크면 양의 연관성이 있습니다.
- 1이면 서로 독립적인 관계입니다.
- 1보다 작으면 음의 연관성이 있습니다.

※ 향상도는 메뉴 사이의 통계적 연관성을 나타내며, 한 메뉴가 다른 메뉴의 원인이라는 뜻은 아닙니다.
""")
