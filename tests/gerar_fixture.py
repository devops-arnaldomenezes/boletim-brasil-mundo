"""Gera notícias FICTÍCIAS para testar o pipeline sem acesso à internet."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

base = [
    ("brasil", "Congresso aprova projeto de lei sobre orçamento", "Senado e Câmara concluem votação do projeto de lei orçamentária.", ["politica"]),
    ("brasil", "Banco Central mantém taxa Selic", "Comitê de política monetária decide manter os juros e cita inflação.", ["economia"]),
    ("brasil", "IBGE divulga dados de emprego do trimestre", "Taxa de desemprego recua segundo a pesquisa do IBGE.", ["economia"]),
    ("brasil", "Fiocruz anuncia estudo sobre vacina contra dengue", "Pesquisa da Fiocruz avalia nova vacina para dengue no SUS.", ["saude"]),
    ("brasil", "Ministério da Saúde amplia campanha de vacinação", "Campanha de vacinação chega a novos municípios.", ["saude"]),
    ("brasil", "Startup brasileira lança modelo de inteligência artificial em português", "Modelo de linguagem treinado em português é apresentado.", ["ia"]),
    ("brasil", "Festival de cinema de São Paulo anuncia programação", "Mostra de cinema traz filmes de 60 países.", ["cultura"]),
    ("brasil", "STF julga ação sobre regulação das redes sociais", "Supremo retoma julgamento sobre plataformas de internet.", ["politica", "tecnologia"]),
    ("global", "ONU alerta para crise humanitária e pede financiamento", "Agências da ONU pedem recursos para ajuda humanitária.", ["politica"]),
    ("global", "OMS publica relatório sobre saúde mental", "Organização Mundial da Saúde recomenda ampliar serviços de saúde mental.", ["saude"]),
    ("global", "FMI revisa projeção de crescimento global", "Fundo Monetário Internacional atualiza estimativa do PIB mundial.", ["economia"]),
    ("global", "UNESCO inscreve novos sítios como patrimônio", "Comitê do patrimônio mundial aprova novas inscrições.", ["cultura"]),
    ("europa", "Parlamento Europeu vota regras para inteligência artificial", "Eurodeputados aprovam ajustes no AI Act.", ["ia", "politica"]),
    ("europa", "BCE decide sobre taxa de juros da zona do euro", "Banco Central Europeu comenta inflação e crescimento.", ["economia"]),
    ("europa", "Comissão Europeia apresenta plano para chips", "Plano busca ampliar produção de semicondutores na Europa.", ["tecnologia"]),
    ("europa", "Eleições regionais na Alemanha", "Partidos disputam votos em eleição regional.", ["politica"]),
    ("europa", "Museu do Louvre anuncia nova exposição", "Exposição reúne obras de arte do Renascimento.", ["cultura"]),
    ("europa", "Agência europeia de medicamentos aprova tratamento", "Novo tratamento contra câncer recebe parecer favorável.", ["saude"]),
    ("eua", "Federal Reserve sinaliza próximos passos dos juros", "Fed avalia dados de inflação e emprego.", ["economia"]),
    ("eua", "Congresso dos EUA debate orçamento federal", "Senado americano discute prazo do orçamento.", ["politica"]),
    ("eua", "Empresa de IA anuncia novo modelo de linguagem", "Lançamento promete avanços em raciocínio e programação.", ["ia"]),
    ("eua", "NASA divulga resultados de missão espacial", "Satélite envia novos dados científicos.", ["tecnologia"]),
    ("eua", "NIH financia pesquisa sobre Alzheimer", "Institutos Nacionais de Saúde anunciam programa de pesquisa.", ["saude"]),
    ("eua", "Big techs enfrentam processo antitruste", "Departamento de Justiça amplia investigação sobre tecnologia.", ["tecnologia"]),
    ("eua", "Prêmio de música anuncia indicados", "Lista de indicados destaca artistas latinos.", ["cultura"]),
    ("asia", "China divulga dados do PIB e comércio exterior", "Exportações chinesas crescem no período.", ["economia"]),
    ("asia", "Japão aprova pacote de estímulo econômico", "Governo japonês anuncia medidas fiscais.", ["economia", "politica"]),
    ("asia", "Coreia do Sul investe em semicondutores e IA", "Plano nacional destina recursos a chips de inteligência artificial.", ["ia", "tecnologia"]),
    ("asia", "Índia lança satélite de observação", "Agência espacial indiana conclui lançamento.", ["tecnologia"]),
    ("asia", "Cúpula da ASEAN discute comércio regional", "Líderes asiáticos tratam de tarifas e cooperação.", ["politica", "economia"]),
    ("asia", "Surto de doença respiratória monitorado na Ásia", "Autoridades de saúde reforçam vigilância.", ["saude"]),
    ("brasil", "Susep divulga arrecadação do mercado de seguros no trimestre", "Seguradoras ampliam prêmios; corretores de seguros puxam vendas de seguro de vida.", ["seguros"]),
    ("brasil", "Fenacor discute regras para corretoras de seguros", "Federação dos corretores debate norma da Susep sobre intermediação.", ["seguros"]),
    ("europa", "Reinsurers renew contracts as catastrophe losses rise", "Reinsurance prices climb after insurers report higher claims.", ["seguros"]),
    ("asia", "Festival de cinema de Busan premia filmes", "Filmes asiáticos são destaque do festival.", ["cultura"]),
]
agora = datetime.now(timezone.utc)
itens = []
for i, (reg, t, r, cats) in enumerate(base):
    itens.append({"titulo": t, "resumo": r + " (notícia fictícia de teste)", "link": f"https://exemplo.org/{i}",
                  "fonte": f"Fonte de teste {reg}", "regiao": reg, "idioma": "pt", "tipo": "imprensa",
                  "publicado": (agora - timedelta(hours=i % 20)).isoformat(), "dicas": cats, "categorias": [],
                  "relevancia": 0.0, "id": f"t{i:03d}"})
Path(__file__).parent.joinpath("fixtures/noticias.json").write_text(json.dumps(itens, ensure_ascii=False, indent=1))
print(len(itens))
