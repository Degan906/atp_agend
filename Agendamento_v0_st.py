import streamlit as st
from jira import JIRA
from datetime import datetime, timedelta
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Agendamentos", layout="wide")

# URL do logotipo
LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRCx0Ywq0Bhihr0RLdHbBrqyuCsRLoV2KLs2g&s"

# Função para conectar ao Jira
def connect_to_jira():
    jira_url = "https://carboncars.atlassian.net"
    email = "henrique.degan@oatsolutions.com.br"
    api_token = "b4mAs0sXJCx3101YvgkhBD3F"
    try:
        jira = JIRA(server=jira_url, basic_auth=(email, api_token))
        return jira
    except Exception as e:
        st.error(f"Erro ao conectar ao Jira: {e}")
        return None

# Função para buscar os agendamentos por dia
def get_issues_by_day(jira):
    jql_query = ('project = "Assistência Técnica Piloto" AND type = AT AND '
                 '"Tipo de Atendimento[Dropdown]" = "SP Interno" AND status NOT IN (Cancelado, Concluído) AND '
                 '"Data de Agendamento do Recebimento[Date]" >= startOfMonth() AND '
                 '"Data de Agendamento do Recebimento[Date]" <= endOfMonth()')
    issues = []
    start_at = 0
    max_results = 100
    while True:
        batch = jira.search_issues(jql_query, fields=[
            "customfield_11747", "summary", "customfield_11298", "customfield_10253",
            "customfield_11725", "customfield_12068", "reporter", "status"
        ], startAt=start_at, maxResults=max_results)
        if not batch:
            break
        issues.extend(batch)
        start_at += max_results
    issue_count = {}
    for issue in issues:
        agendamento = issue.fields.customfield_11747
        if agendamento:
            date_key = datetime.strptime(agendamento, "%Y-%m-%d").date()
            issue_count[date_key] = issue_count.get(date_key, []) + [issue]
    return issue_count

# Função para criar o calendário interativo com navegação por mês
def create_calendar(issues_by_day):
    # Estado para armazenar o mês atual
    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.now().month
    if 'current_year' not in st.session_state:
        st.session_state.current_year = datetime.now().year

    current_year = st.session_state.current_year
    current_month = st.session_state.current_month
    today = datetime.now().date()

    first_day = datetime(current_year, current_month, 1).date()
    last_day = (datetime(current_year + (current_month // 12),
                         ((current_month % 12) + 1), 1) - timedelta(days=1)).date()
    days_in_month = last_day.day
    first_weekday = first_day.weekday()  # 0=segunda ... 4=sexta, 5=sábado, 6=domingo

    weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    st.markdown("<h3 style='text-align:center;'>📅 Calendário</h3>", unsafe_allow_html=True)

    # Navegação de meses
    col_prev, col_title, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("⬅️ Anterior"):
            if current_month == 1:
                st.session_state.current_month = 12
                st.session_state.current_year -= 1
            else:
                st.session_state.current_month -= 1
            st.rerun()
    with col_next:
        if st.button("Próximo ➡️"):
            if current_month == 12:
                st.session_state.current_month = 1
                st.session_state.current_year += 1
            else:
                st.session_state.current_month += 1
            st.rerun()
    with col_title:
        st.markdown(f"<h4 style='text-align:center;'>{first_day.strftime('%B %Y')}</h4>", unsafe_allow_html=True)

    # Cabeçalho da semana
    cols = st.columns(7)
    for i, day in enumerate(weekdays):
        cols[i].markdown(f"<div style='text-align:center; font-weight:bold;'>{day}</div>", unsafe_allow_html=True)

    # Preenchimento do calendário
    current_row = []
    calendar_rows = []

    # Dias vazios antes do início do mês
    for _ in range(first_weekday):
        current_row.append(None)

    for day in range(1, days_in_month + 1):
        date_key = datetime(current_year, current_month, day).date()
        issues = issues_by_day.get(date_key, [])
        issue_count = len(issues)
        is_today = today == date_key
        is_weekend = date_key.weekday() >= 5

        bgcolor = "#fa0202" if is_weekend else "#808080" if is_today else "#fca438" if issue_count > 0 else "#ffffff"
        text_color = "#000000" if bgcolor == "#FFFF00" or bgcolor == "#ffffff" else "#ffffff"

        current_row.append((day, date_key, issue_count, bgcolor, text_color))
        if len(current_row) == 7:
            calendar_rows.append(current_row)
            current_row = []

    if current_row:
        while len(current_row) < 7:
            current_row.append(None)
        calendar_rows.append(current_row)

    for row in calendar_rows:
        cols = st.columns(7)
        for i, cell in enumerate(row):
            if cell:
                day, date_key, issue_count, bgcolor, text_color = cell
                with cols[i]:
                    card_html = f"""
                    <div style='width:100%; height:100px; background-color:{bgcolor}; color:{text_color};
                                display:flex; flex-direction:column; align-items:center; justify-content:center;
                                border-radius:8px; cursor:pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'
                                onclick="document.getElementById('selected_date').value='{date_key}';">
                        <span style='font-size:16px; font-weight:normal;'>{day}</span>
                        <span style='font-size:20px; font-weight:bold;'>🚗 {issue_count}</span>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button(f"Ver {day}", key=f"btn_{date_key}"):
                        st.session_state.selected_date = date_key
                        st.session_state.view = "day_details"
                        st.rerun()
            else:
                cols[i].empty()

# Função para exibir os agendamentos de um dia específico
def show_issues_for_date(selected_date, issues_by_day):
    issues = issues_by_day.get(selected_date, [])
    st.title(f"📅 Agendamentos para {selected_date.strftime('%d/%m/%Y')}")

    if not issues:
        st.info("Nenhum agendamento encontrado para esta data.")
        if st.button("⬅️ Voltar ao Calendário"):
            st.session_state.view = "calendar"
            st.rerun()
        return

    # Preparando dados para DataFrame
    data = []
    for idx, issue in enumerate(issues):
        tipo_servico = ", ".join([opt.value for opt in issue.fields.customfield_11725]) if issue.fields.customfield_11725 else "-"
        placa = issue.fields.customfield_10253 or "-"
        consultor = str(issue.fields.customfield_12068) if issue.fields.customfield_12068 else "-"

        data.append({
            "Nº": idx + 1,
            "Veículo": issue.fields.customfield_11298,
            "Placa": placa,
            "Tipo de Serviço": tipo_servico,
            "Consultor": consultor,
            "Criador": issue.fields.reporter.displayName,
            "Status": issue.fields.status.name,
            "Confirmado": False
        })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df,
        column_config={
            "Confirmado": st.column_config.CheckboxColumn("Confirmado", help="Marque para confirmar a chegada")
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Nº", "Veículo", "Placa", "Tipo de Serviço", "Consultor", "Criador", "Status"]
    )

    confirmed = edited_df[edited_df["Confirmado"]]
    if not confirmed.empty:
        st.subheader("✅ Veículos Confirmados")
        st.dataframe(confirmed.drop(columns=["Confirmado"]), use_container_width=True)

    if st.button("⬅️ Voltar ao Calendário"):
        st.session_state.view = "calendar"
        st.rerun()

# Tela principal
def show_main_screen():
    # CSS personalizado
    st.markdown("""
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #f8f9fa;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #ddd;
    }
    .stButton>button {
        margin: 5px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Logotipo centralizado
    st.markdown(f"<div style='text-align:center;'><img src='{LOGO_URL}' width='150'/></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Dashboard de Agendamentos</h3>", unsafe_allow_html=True)

    # Última atualização
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"<p style='text-align:right;'>Última atualização: {st.session_state.last_update}</p>", unsafe_allow_html=True)

    # Botões
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Atualizar Dados"):
            update_data()
    with col2:
        if st.button("📅 Agendamentos de Hoje"):
            st.session_state.view = "today"
            st.rerun()

    # Conectar ao Jira
    jira = connect_to_jira()
    if jira:
        issues_by_day = get_issues_by_day(jira)

        if st.session_state.get("view") == "today":
            show_issues_for_today(issues_by_day)
        elif st.session_state.get("view") == "day_details":
            selected_date = st.session_state.get("selected_date")
            if selected_date:
                show_issues_for_date(selected_date, issues_by_day)
        else:
            create_calendar(issues_by_day)

    # Rodapé
    st.markdown(f"""
    <div class="footer">
        Usuário logado: admin | Login realizado em: {st.session_state.get('login_time', 'N/A')}
    </div>
    """, unsafe_allow_html=True)

# Função para atualizar os dados
def update_data():
    st.session_state.last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.rerun()

# Função para exibir os agendamentos de hoje
def show_issues_for_today(issues_by_day):
    today = datetime.now().date()
    issues = issues_by_day.get(today, [])
    st.title(f"📅 Agendamentos para Hoje ({today.strftime('%d/%m/%Y')})")

    if not issues:
        st.info("Nenhum agendamento encontrado para hoje.")
        if st.button("⬅️ Voltar ao Calendário"):
            st.session_state.view = "calendar"
            st.rerun()
        return

    data = []
    for idx, issue in enumerate(issues):
        tipo_servico = ", ".join([opt.value for opt in issue.fields.customfield_11725]) if issue.fields.customfield_11725 else "-"
        placa = issue.fields.customfield_10253 or "-"
        consultor = str(issue.fields.customfield_12068) if issue.fields.customfield_12068 else "-"

        data.append({
            "Nº": idx + 1,
            "Veículo": issue.fields.customfield_11298,
            "Placa": placa,
            "Tipo de Serviço": tipo_servico,
            "Consultor": consultor,
            "Criador": issue.fields.reporter.displayName,
            "Status": issue.fields.status.name,
            "Confirmado": False
        })

    edited_df = st.data_editor(
        pd.DataFrame(data),
        column_config={"Confirmado": st.column_config.CheckboxColumn("Confirmado")},
        use_container_width=True,
        hide_index=True,
        disabled=["Nº", "Veículo", "Placa", "Tipo de Serviço", "Consultor", "Criador", "Status"]
    )

    confirmed = edited_df[edited_df["Confirmado"]]
    if not confirmed.empty:
        st.subheader("✅ Veículos Confirmados")
        st.dataframe(confirmed.drop(columns=["Confirmado"]), use_container_width=True)

    if st.button("⬅️ Voltar ao Calendário"):
        st.session_state.view = "calendar"
        st.rerun()

# Tela de login
def show_login_screen():
    st.markdown(f"<div style='text-align:center;'><img src='{LOGO_URL}' width='150'/></div>", unsafe_allow_html=True)
    st.title("🔒 Acesso Restrito")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.session_state.login_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")

# Fluxo principal
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    show_main_screen()
else:
    show_login_screen()
