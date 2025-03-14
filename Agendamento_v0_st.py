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
        st.success("Conexão bem-sucedida!")
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

# Função para criar o calendário interativo
def create_calendar(issues_by_day, jira, total_issues):
    today = datetime.now().date()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    first_weekday = first_day.weekday()

    # Definindo os dias da semana em português
    weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    # Cabeçalho com os dias da semana
    st.markdown("<div style='text-align:center; font-weight:bold; margin-bottom: 10px;'>Calendário</div>", unsafe_allow_html=True)
    cols = st.columns(len(weekdays))
    for i, day in enumerate(weekdays):
        cols[i].markdown(f"<div style='text-align:center; font-weight:bold;'>{day}</div>", unsafe_allow_html=True)

    # Calculando os dias do mês
    days_in_month = last_day.day

    # Adicionar os containers dos dias
    current_row = []  # Contém os containers de uma semana
    calendar_rows = []

    # Adiciona contêineres vazios para os dias antes do início do mês
    for _ in range(first_weekday):
        current_row.append(None)

    for day in range(1, days_in_month + 1):
        date_key = datetime(today.year, today.month, day).date()
        issue_count = len(issues_by_day.get(date_key, []))
        is_today = today == date_key
        is_weekend = date_key.weekday() >= 5  # Sábado ou domingo

        # Estilos de cor baseados no dia
        bgcolor = "#fa0202" if is_weekend else "#FFFF00" if is_today else "#fca438" if issue_count > 0 else "#ffffff"
        text_color = "#000000" if bgcolor == "#FFFF00" else "#ffffff" if bgcolor == "#fa0202" else "#000000"  # Cor do texto ajustada para contraste

        # Criar o conteúdo do dia como um card HTML
        button_key = f"button_{date_key}"
        current_row.append((day, date_key, issue_count, bgcolor, text_color))

        # Se a semana tiver 7 dias, adiciona a linha de semana e começa uma nova
        if len(current_row) == 7:
            calendar_rows.append(current_row)
            current_row = []

    # Adiciona a última semana, caso não tenha completado 7 dias
    if current_row:
        while len(current_row) < 7:  # Completa a linha com contêineres vazios
            current_row.append(None)
        calendar_rows.append(current_row)

    # Exibir o calendário
    for row in calendar_rows:
        cols = st.columns(7)
        for i, cell in enumerate(row):
            if cell:
                day, date_key, issue_count, bgcolor, text_color = cell
                with cols[i]:
                    # Card estilizado com HTML personalizado
                    card_html = f"""
                    <div style='width:100%; height:100px; background-color:{bgcolor}; color:{text_color};
                                display:flex; flex-direction:column; align-items:center; justify-content:center;
                                border:1px solid #ddd; border-radius:10px; cursor:pointer; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);'
                                onclick="document.getElementById('selected_date').value='{date_key}';">
                        <span style='font-size:18px; font-weight:normal;'>{day}</span>
                        <span style='font-size:24px; font-weight:bold;'>🚗 {issue_count}</span>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

                    # Capturar clique no card
                    if st.session_state.get('selected_date') == date_key:
                        show_issues_for_date(date_key, issues_by_day)
            else:
                cols[i].markdown("<div style='width:100%; height:100px;'></div>", unsafe_allow_html=True)

    # Captura a data selecionada
    selected_date = st.session_state.get('selected_date')
    if selected_date:
        show_issues_for_date(selected_date, issues_by_day)

# Função para exibir as issues de uma data específica
def show_issues_for_date(selected_date, issues_by_day):
    issues = issues_by_day.get(selected_date, [])
    if not issues:
        st.info(f"Nenhum agendamento encontrado para {selected_date.strftime('%d/%m/%Y')}. 😊")
        if st.button("⬅️ Voltar ao Calendário"):
            st.session_state.selected_date = None
            st.rerun()
        return

    # Criar uma lista de dicionários com os dados
    data = []
    for issue in issues:
        tipo_servico = ", ".join([option.value for option in issue.fields.customfield_11725]) if issue.fields.customfield_11725 else ""
        consultores = str(issue.fields.customfield_12068) if issue.fields.customfield_12068 else ""

        data.append({
            "Key": issue.key,
            "Data de Agendamento": issue.fields.customfield_11747,
            "Veículo": issue.fields.customfield_11298,
            "Placa": issue.fields.customfield_10253,
            "Tipo de Serviço": tipo_servico,
            "Consultores": consultores,
            "Criador": issue.fields.reporter.displayName,
            "Status": issue.fields.status.name,
            "Confirmado": False  # Adiciona o campo "Confirmado" com valor inicial False
        })

    # Converter para DataFrame
    df = pd.DataFrame(data)

    # Adicionar coluna de numeração, se ainda não existir
    if "Nº" not in df.columns:
        df.insert(0, "Nº", range(1, len(df) + 1))

    # Exibir a tabela responsiva com checkbox
    st.subheader(f"📅 Agendamentos para {selected_date.strftime('%d/%m/%Y')} ({len(df)} total)")

    # Usar st.data_editor para permitir edição
    edited_data = st.data_editor(
        df,
        column_config={
            "Confirmado": st.column_config.CheckboxColumn(
                "Confirmado", help="Marque para confirmar a chegada do veículo"
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Key", "Data de Agendamento", "Veículo", "Placa", "Tipo de Serviço", "Consultores", "Criador", "Status"]
    )

    # Filtrar apenas os veículos confirmados
    confirmed_data = edited_data[edited_data["Confirmado"]]

    # Adicionar coluna de numeração à tabela de Veículos Confirmados, se ainda não existir
    if "Nº" not in confirmed_data.columns:
        confirmed_data.insert(0, "Nº", range(1, len(confirmed_data) + 1))

    # Exibir a tabela de Veículos Confirmados
    st.subheader(f"📝 Veículos Confirmados ({len(confirmed_data)} total)")
    if confirmed_data.empty:
        st.info("Nenhum veículo confirmado ainda.")
    else:
        st.dataframe(confirmed_data.drop(columns=["Confirmado"]), use_container_width=True)

    # Botão para voltar ao calendário
    if st.button("⬅️ Voltar ao Calendário"):
        st.session_state.selected_date = None
        st.rerun()

# Função para exibir as issues agendadas para hoje
def show_issues_for_today(issues_by_day):
    today = datetime.now().date()
    issues = issues_by_day.get(today, [])
    if not issues:
        st.info(f"🎉 Nenhum agendamento para hoje ({today.strftime('%d/%m/%Y')}). Aproveite o dia! 🎉")
        if st.button("⬅️ Voltar ao Calendário"):
            st.session_state.view = "calendar"
            st.rerun()
        return

    # Criar uma lista de dicionários com os dados
    data = []
    for issue in issues:
        tipo_servico = ", ".join([option.value for option in issue.fields.customfield_11725]) if issue.fields.customfield_11725 else ""
        consultores = str(issue.fields.customfield_12068) if issue.fields.customfield_12068 else ""

        data.append({
            "Key": issue.key,
            "Data de Agendamento": issue.fields.customfield_11747,
            "Veículo": issue.fields.customfield_11298,
            "Placa": issue.fields.customfield_10253,
            "Tipo de Serviço": tipo_servico,
            "Consultores": consultores,
            "Criador": issue.fields.reporter.displayName,
            "Status": issue.fields.status.name,
            "Confirmado": False  # Adiciona o campo "Confirmado" com valor inicial False
        })

    # Converter para DataFrame
    df = pd.DataFrame(data)

    # Adicionar coluna de numeração, se ainda não existir
    if "Nº" not in df.columns:
        df.insert(0, "Nº", range(1, len(df) + 1))

    # Exibir a tabela responsiva com checkbox
    st.subheader(f"📅 Agendamentos para Hoje ({today.strftime('%d/%m/%Y')}) ({len(df)} total)")

    # Usar st.data_editor para permitir edição
    edited_data = st.data_editor(
        df,
        column_config={
            "Confirmado": st.column_config.CheckboxColumn(
                "Confirmado", help="Marque para confirmar a chegada do veículo"
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Key", "Data de Agendamento", "Veículo", "Placa", "Tipo de Serviço", "Consultores", "Criador", "Status"]
    )

    # Filtrar apenas os veículos confirmados
    confirmed_data = edited_data[edited_data["Confirmado"]]

    # Adicionar coluna de numeração à tabela de Veículos Confirmados, se ainda não existir
    if "Nº" not in confirmed_data.columns:
        confirmed_data.insert(0, "Nº", range(1, len(confirmed_data) + 1))

    # Exibir a tabela de Veículos Confirmados
    st.subheader(f"📝 Veículos Confirmados ({len(confirmed_data)} total)")
    if confirmed_data.empty:
        st.info("Nenhum veículo confirmado ainda.")
    else:
        st.dataframe(confirmed_data.drop(columns=["Confirmado"]), use_container_width=True)

    # Botão para voltar ao calendário
    if st.button("⬅️ Voltar ao Calendário"):
        st.session_state.view = "calendar"
        st.rerun()

# Tela principal
def show_main_screen():
    # CSS personalizado para responsividade
    st.markdown(
        """
        <style>
        .main-container {
            max-width: 100%;
            padding: 1rem;
        }
        .stButton>button {
            width: auto;
            margin: 0.5rem 0.5rem;
            padding: 0.5rem 1rem;
        }
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
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Exibir o logotipo no topo centralizado
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="{LOGO_URL}" alt="Logo" style="width: 150px; margin-bottom: 20px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Inicializar a variável de estado para a última atualização
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Barra superior com informações e botões
    st.markdown(
        f"<div style='text-align: right; margin-bottom: 10px;'>Última atualização: {st.session_state.last_update}</div>",
        unsafe_allow_html=True,
    )

    # Botões lado a lado
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Atualizar"):
            update_data()
    with col2:
        if st.button("📅 Agendados para Hoje"):
            st.session_state.view = "today"
            st.rerun()

    # Conectar ao Jira e exibir o calendário ou a tela de hoje
    current_jira = connect_to_jira()
    if current_jira:
        issues_by_day = get_issues_by_day(current_jira)
        if st.session_state.get("view") == "today":
            show_issues_for_today(issues_by_day)
        else:
            create_calendar(issues_by_day, current_jira, len(issues_by_day))

    # Rodapé com informações do usuário logado
    st.markdown(
        f"""
        <div class="footer">
            Usuário logado: admin | Login realizado em: {st.session_state.get('login_time', 'N/A')}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Função para atualizar os dados
def update_data():
    st.session_state.last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.rerun()  # Força a atualização da tela

# Mostrar tela de login
def show_login_screen():
    # Exibir o logotipo no topo centralizado
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="{LOGO_URL}" alt="Logo" style="width: 150px; margin-bottom: 20px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("🔒 Agendamentos Carbon")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username == "admin" and password == "admin":
            st.session_state.logged_in = True
            st.session_state.login_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            st.rerun()  # Força a atualização da tela após o login
        else:
            st.error("❌ Usuário ou senha incorretos.")

# Inicia a aplicação
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
        show_main_screen()
else:
    show_login_screen()
