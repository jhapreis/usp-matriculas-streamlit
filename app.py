import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Planner de Grade 2027.1",
    page_icon="📅",
    layout="wide"
)

ARQUIVO_JSON = Path(__file__).parent / "disciplinas.json"
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex"]
HORARIOS = [
    "08h10 - 09h50",
    "10h10 - 11h50",
    "12h00 - 14h20",
    "14h20 - 16h00",
    "16h20 - 18h00"
]
FAIXA_TRABALHO = {"10h10 - 11h50", "14h20 - 16h00"}
META_CREDITOS = 12


def carregar_disciplinas():
    if not ARQUIVO_JSON.exists():
        st.error(f"Arquivo não encontrado: {ARQUIVO_JSON}")
        st.stop()
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_disciplinas(lista):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


disciplinas = carregar_disciplinas()

# Inicializa o estado das seleções (começa vazio para acumular 1 por 1)
for d in disciplinas:
    chave = f"sel_{d['id']}"
    if chave not in st.session_state:
        st.session_state[chave] = False


def aplicar_preset(ids_alvo):
    for d in disciplinas:
        st.session_state[f"sel_{d['id']}"] = d["id"] in ids_alvo


def ao_alternar_disciplina(disc_atual):
    chave_atual = f"sel_{disc_atual['id']}"
    grupo = disc_atual.get("grupo_exclusivo")
    # Se ativou uma turma de grupo exclusivo (ex: 7600015), desmarca a outra turma
    if st.session_state[chave_atual] and grupo:
        for outra in disciplinas:
            if outra["id"] != disc_atual["id"] and outra.get("grupo_exclusivo") == grupo:
                st.session_state[f"sel_{outra['id']}"] = False


# --- CABEÇALHO E ATALHOS ---
st.title("📅 Planner Interativo de Grade — 2027.1")
st.caption("Ative as disciplinas uma por uma na barra lateral para visualizar o acúmulo na grade, os créditos e os horários livres para trabalho (10h–16h).")

b1, b2, b3, b4 = st.columns(4)
b1.button("🧹 Zerar grade", on_click=aplicar_preset, args=(set(),), use_container_width=True)
b2.button("⚡ Sugestão 12 créd. (Lab Ter)", on_click=aplicar_preset, args=({"7600015_T02", "7600020", "SCC0240"},), use_container_width=True)
b3.button("⚡ Sugestão 12 créd. (Lab Qui)", on_click=aplicar_preset, args=({"7600015_T04", "7600020", "SCC0240"},), use_container_width=True)
b4.button("🛡️ Sugestão 16 créd. (+Mat. Fin.)", on_click=aplicar_preset, args=({"7600015_T02", "7600020", "SCC0240", "7600135"},), use_container_width=True)

# --- MAPA ATUAL DA GRADE ---
selecionadas = [d for d in disciplinas if st.session_state.get(f"sel_{d['id']}", False)]
grade = {(dia, hr): [] for dia in DIAS for hr in HORARIOS}

for d in selecionadas:
    for dia, hr in d["horarios"]:
        grade[(dia, hr)].append(d)


def status_previo(disc):
    """Indica antes mesmo de clicar se a matéria encaixa, ocupa trabalho ou conflita."""
    if st.session_state.get(f"sel_{disc['id']}", False):
        return "✅ Na grade"

    choques = set()
    troca_turma = False
    ocupa_trabalho = False

    for dia, hr in disc["horarios"]:
        if hr in FAIXA_TRABALHO:
            ocupa_trabalho = True
        for existente in grade[(dia, hr)]:
            if disc.get("grupo_exclusivo") and existente.get("grupo_exclusivo") == disc["grupo_exclusivo"]:
                troca_turma = True
            else:
                choques.add(existente["codigo"])

    if choques:
        return f"🔴 Conflita c/ {', '.join(sorted(choques))}"
    if troca_turma:
        return "🔄 Substitui outra turma"
    if ocupa_trabalho:
        return "🟡 Encaixa (usa 10h–16h)"
    return "🟢 Encaixa (fora 10h–16h)"


# --- BARRA LATERAL: SELEÇÃO PASSO A PASSO ---
with st.sidebar:
    st.header("Monte sua grade (1 por 1)")
    categorias = ["Obrigatória", "Opcional", "Opcional (7º sem.)"]

    for cat in categorias:
        grupo_cat = [d for d in disciplinas if d["categoria"] == cat]
        if not grupo_cat:
            continue
        st.subheader(cat)
        for d in grupo_cat:
            horarios_txt = " | ".join(f"{dia} {hr}" for dia, hr in d["horarios"])
            badge = status_previo(d)
            st.toggle(
                label=f"**{d['codigo']}** — {d['nome']} ({d['creditos']} créd.)",
                key=f"sel_{d['id']}",
                on_change=ao_alternar_disciplina,
                args=(d,),
                help=f"Docente: {d['docente']} | Local: {d['local']}"
            )
            st.caption(f"{badge} · `{horarios_txt}`")

    st.divider()
    with st.expander("➕ Adicionar nova matéria ao JSON"):
        with st.form("form_nova_disc", clear_on_submit=True):
            novo_cod = st.text_input("Código (ex: 7600046)")
            novo_nome = st.text_input("Nome da disciplina")
            nova_cat = st.selectbox("Categoria", ["Obrigatória", "Opcional", "Opcional (7º sem.)"])
            novos_cred = st.number_input("Créditos", min_value=1, max_value=12, value=4)
            novo_doc = st.text_input("Docente", value="A confirmar")
            novo_loc = st.text_input("Local", value="A confirmar")
            c_dia1, c_hr1 = st.columns(2)
            dia1 = c_dia1.selectbox("Dia 1", DIAS, key="d1")
            hr1 = c_hr1.selectbox("Horário 1", [h for h in HORARIOS if h != "12h00 - 14h20"], key="h1")
            usar_slot2 = st.checkbox("Possui 2º horário na semana?")
            c_dia2, c_hr2 = st.columns(2)
            dia2 = c_dia2.selectbox("Dia 2", DIAS, index=2, key="d2")
            hr2 = c_hr2.selectbox("Horário 2", [h for h in HORARIOS if h != "12h00 - 14h20"], key="h2")

            if st.form_submit_button("Salvar no disciplinas.json"):
                if novo_cod.strip() and novo_nome.strip():
                    slots = [[dia1, hr1]]
                    if usar_slot2 and [dia2, hr2] != [dia1, hr1]:
                        slots.append([dia2, hr2])
                    novo_id = f"{novo_cod.strip()}_{len(disciplinas)+1}"
                    disciplinas.append({
                        "id": novo_id,
                        "codigo": novo_cod.strip(),
                        "nome": novo_nome.strip(),
                        "categoria": nova_cat,
                        "grupo_exclusivo": None,
                        "creditos": int(novos_cred),
                        "docente": novo_doc.strip(),
                        "local": novo_loc.strip(),
                        "horarios": slots
                    })
                    salvar_disciplinas(disciplinas)
                    st.rerun()

# --- CÁLCULO DOS INDICADORES ---
total_creditos = sum(d["creditos"] for d in selecionadas)
blocos_trabalho_ocupados = sum(
    1 for dia in DIAS for hr in FAIXA_TRABALHO if len(grade[(dia, hr)]) > 0
)
blocos_trabalho_livres = 10 - blocos_trabalho_ocupados
dias_livres = sum(
    1 for dia in DIAS if all(len(grade[(dia, hr)]) == 0 for hr in HORARIOS)
)
conflitos = [
    f"{dia} ({hr}): {' + '.join(x['codigo'] for x in grade[(dia, hr)])}"
    for dia in DIAS for hr in HORARIOS if len(grade[(dia, hr)]) > 1
]

# --- PAINEL DE MÉTRICAS ---
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "Créditos Acumulados",
    f"{total_creditos} / {META_CREDITOS}",
    delta="Meta atingida" if total_creditos >= META_CREDITOS else f"Faltam {META_CREDITOS - total_creditos}",
    delta_color="normal" if total_creditos >= META_CREDITOS else "inverse"
)
m2.metric(
    "Blocos Trabalho (10h–16h)",
    f"{blocos_trabalho_livres} / 10 livres",
    delta=f"{blocos_trabalho_ocupados} ocupado(s)",
    delta_color="off"
)
m3.metric(
    "Dias 100% Livres",
    f"{dias_livres} / 5 dias"
)
m4.metric(
    "Conflitos",
    len(conflitos),
    delta="Nenhum choque" if not conflitos else "Sobreposto",
    delta_color="normal" if not conflitos else "inverse"
)

st.progress(min(total_creditos / META_CREDITOS, 1.0))

if conflitos:
    st.error("⚠️ **Choque de horário detectado:** " + " | ".join(conflitos))

# --- CONSTRUÇÃO DA TABELA NATIVA DO PLANNER ---
dados_tabela = {}
tipos_celula = {}

for dia in DIAS:
    col_texto = []
    col_tipo = []
    for hr in HORARIOS:
        if hr == "12h00 - 14h20":
            col_texto.append("Almoço / Trabalho")
            col_tipo.append("almoco")
            continue

        itens = grade[(dia, hr)]
        if len(itens) > 1:
            col_texto.append("⚡ CONFLITO: " + " + ".join(x["codigo"] for x in itens))
            col_tipo.append("conflito")
        elif len(itens) == 1:
            x = itens[0]
            col_texto.append(f"{x['codigo']} — {x['nome']} ({x['local']})")
            col_tipo.append("obrig" if x["categoria"] == "Obrigatória" else "opt")
        else:
            if hr in FAIXA_TRABALHO:
                col_texto.append("Livre (Trabalho)")
                col_tipo.append("trabalho")
            else:
                col_texto.append("Livre")
                col_tipo.append("livre")

    dados_tabela[dia] = col_texto
    tipos_celula[dia] = col_tipo

df_grade = pd.DataFrame(dados_tabela, index=HORARIOS)
df_tipos = pd.DataFrame(tipos_celula, index=HORARIOS)

CORES = {
    "obrig": "background-color: #dcfce7; color: #14532d; font-weight: 600;",
    "opt": "background-color: #fef3c7; color: #78350f; font-weight: 600;",
    "conflito": "background-color: #fee2e2; color: #7f1d1d; font-weight: 700;",
    "trabalho": "background-color: #dbeafe; color: #1e3a8a;",
    "almoco": "background-color: #e2e8f0; color: #334155; font-style: italic;",
    "livre": "background-color: #f8fafc; color: #64748b;"
}


def estilizar_grade(_):
    return df_tipos.replace(CORES)


st.subheader("Grade Semanal")
st.dataframe(
    df_grade.style.apply(estilizar_grade, axis=None),
    use_container_width=True,
    height=235
)

if selecionadas:
    st.subheader("Resumo das Matérias Selecionadas")
    df_resumo = pd.DataFrame([
        {
            "Código": d["codigo"],
            "Disciplina": d["nome"],
            "Categoria": d["categoria"],
            "Créditos": d["creditos"],
            "Horários": ", ".join(f"{dia} ({hr})" for dia, hr in d["horarios"]),
            "Docente": d["docente"],
            "Local": d["local"]
        }
        for d in selecionadas
    ])
    st.dataframe(df_resumo, use_container_width=True, hide_index=True)