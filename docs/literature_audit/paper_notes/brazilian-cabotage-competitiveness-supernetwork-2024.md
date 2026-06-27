# Paper Note: Brazilian maritime containerized cabotage competitiveness assessment based on a multimodal super network

* **Full Title**: Brazilian maritime containerized cabotage competitiveness assessment based on a multimodal super network
* **Year**: 2024
* **Local File Path / Citation Key**: `docs/references/core/brazilian-cabotage-competitiveness-supernetwork-2024.pdf` / `competitiveness2024`
* **Review Status**: reviewed
* **What part of the paper was actually read**: Abstract, Introduction, Tables, and specific methodology sections focusing on costs and emissions boundaries via automated extraction using a local python script with the `pypdf` library.
* **Key claims relevant to CabotageLens**: Cabotage has a significant cost advantage over road for long-haul routes (>1,800 km). Cabotage offers up to 41.3% reduction in CO2e emissions.
* **Exact section/page/table/figure references**: Page 1 (Abstract); Page 10 (Road diesel WTW); Page 20, Table 13 (MDO and VLSFO WTW parameters).
* **Useful quantitative values, with units**: 
  - Cost advantage threshold: >1,800 km
  - CO2e emission reduction: up to 41.3%
  - VLSFO WTW emission factor: 94.26 gCO2eq/MJ
  - MDO WTW emission factor: 92.78 gCO2eq/MJ
  - Road diesel WTW emission factor: 86.50 gCO2eq/MJ
  - Road Transportation Mode EBIT margin: 15%
  - Carbon price: 356.2 BRL/tCO2e
* **Emissions boundary**: WTW / CO2e. Explicitly models Well-to-Tank (WtT) and Tank-to-Wake (TtW).
* **Cost boundary**: Includes freight rates (with an assumed 15% EBIT for road), in-transit inventory costs, and CO2eq emission costs.
* **Route/network modeling boundary**: Uses an adapted All Pairs Shortest Path (APSP) algorithm over a supernetwork, incorporating aggregate pre- and on-carriage distances.
* **Direct implications for CabotageLens methodology**: Validates the integration of first-mile and last-mile in modal comparisons. Nearest-port heuristics should be clearly contrasted with the supernetwork approach used here.
* **Direct implications for validation Batch 001 / Batch 001B**: Highlights the need for accurate distance metrics, as the 1,800 km threshold relies on precise maritime distances.
* **Direct implications for final TF report**: Can strongly support claims about cabotage competitiveness on long-haul routes.
* **Direct implications for technical article**: Provides a WTW CO2eq baseline to compare the model's TTW results.
* **Caveats and non-applicable parts**: The supernetwork approach models 637 cities and detailed service frequencies, which may exceed CabotageLens' simplified routing logic.
* **Claims that should not be borrowed because the boundary differs**: Do not directly compare the WTW emissions factors against CabotageLens' TTW factors without adjusting for the boundary. The paper is extremely useful for comparison but its WTW baseline should not be directly substituted into the TTW model.
* **Recommended citation use**: Strongest citation for multimodal supernetwork methodology, long-haul distance thresholds (1800km), and full WTW cost-inclusive comparisons in Brazil.
