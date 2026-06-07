# System Boundary for the Thesis Model

This note defines the proposed methodological boundary for the thesis comparison
between road-only freight transport and road-cabotage-road multimodal transport
in Brazil. It is intended to support the theoretical framing of the thesis and
to keep the implemented model auditable. It does not introduce new experiments,
data sources, or code requirements.

The boundary should be read as a conservative planning document. Where the
current implementation or available documentation does not prove that a
component is modeled, the component is treated as outside the confirmed model
or as methodology debt.

## 1. Functional Unit

The functional unit is:

> The movement of one defined freight shipment, with the same cargo mass and
> origin-destination demand, between a specified origin and a specified
> destination in Brazil.

For model interpretation, this means:

- The road-only and multimodal alternatives must serve the same transport
  demand.
- The cargo mass, origin, destination, and scenario assumptions must be held
  constant across alternatives.
- Results may be reported per shipment and, when useful for comparison, as
  normalized indicators such as per tonne-kilometre.
- The comparison is not a national freight inventory, a company-wide emissions
  inventory, or a full product life-cycle assessment unless the thesis later
  adds those scopes explicitly.

Recommended wording:

> This study adopts as its functional unit the transport service required to
> move a given freight shipment, with fixed cargo mass, origin, and destination,
> within Brazil. The functional unit is therefore defined by the demanded
> logistics service rather than by a vehicle, route segment, or annual transport
> volume.

## 2. Compared Transport Chains

### 2.1 Road-Only Chain

The road-only chain represents a single road freight alternative:

1. The shipment departs from the origin.
2. It is transported by road along the modeled road route.
3. It arrives at the final destination without a maritime cabotage leg.

Inside this chain, the model boundary includes only the road transport service
that is required to move the shipment between the origin and destination under
the selected scenario assumptions.

Recommended wording:

> The road-only alternative is modeled as a direct land transport chain from the
> origin to the destination. It represents the operational performance of the
> road route required to satisfy the same freight demand used in the multimodal
> alternative.

### 2.2 Road-Cabotage-Road Multimodal Chain

The multimodal chain represents a road-cabotage-road freight alternative:

1. The shipment departs from the origin by road.
2. It travels by road to the selected origin port.
3. It is transported by maritime cabotage between the selected origin and
   destination ports.
4. It travels by road from the destination port to the final destination.

The multimodal alternative should be interpreted as a transport-chain
comparison, not as a claim that every operational detail of port logistics is
represented. Port choice, port eligibility, and maritime leg assumptions should
be described according to the rules and data actually used by the model.

Recommended wording:

> The multimodal alternative is modeled as a three-leg logistics chain composed
> of road access to an origin port, a domestic maritime cabotage leg, and road
> egress from a destination port to the final destination. The comparison
> therefore evaluates whether substituting part of the road distance with a
> cabotage leg changes the modeled emissions and cost indicators for the same
> freight demand.

## 3. Included Components

The confirmed system boundary should include the following components when they
are explicitly parameterized by tracked code and tracked data:

- Origin-destination definition, including coordinates or equivalent location
  inputs used by the model.
- Road route distance and geometry for the road-only alternative.
- Road access and egress route distances and geometries for the multimodal
  alternative.
- Maritime cabotage distance or matrix value between the selected ports.
- Fuel, emissions, and cost calculations for road legs, according to the
  factors and formulas documented in the repository.
- Fuel, emissions, and cost calculations for the cabotage leg, according to the
  factors and formulas documented in the repository.
- Port selection logic used to connect the origin and destination to maritime
  cabotage options.
- Route caching and reuse mechanisms that affect whether external routing calls
  are needed, provided they do not change the underlying scenario definition.
- Direct modeled outputs used for comparison, such as total distance, fuel
  consumption, emissions, and monetary cost where available.

The thesis should distinguish between components that are directly modeled and
components that are only represented indirectly through aggregate factors. For
example, if a cost factor already embeds a typical operational charge, the
thesis should state that the component is included only through that aggregate
factor, not as an independently modeled activity.

Recommended wording:

> The system boundary includes the operational transport activities explicitly
> represented by the model: road movement in the direct road alternative, road
> access and egress in the multimodal alternative, and the cabotage movement
> between selected ports. Distances, fuel use, emissions, and costs are included
> only to the extent that they are calculated from documented model formulas and
> traceable input data.

## 4. Excluded Components

The following components should be treated as outside the confirmed model unless
the thesis later adds explicit data, formulas, and validation for them:

- Manufacturing, maintenance, and end-of-life treatment of trucks, vessels,
  trailers, containers, and handling equipment.
- Construction, maintenance, and depreciation of roads, ports, terminals,
  warehouses, fuel stations, and maritime infrastructure.
- Port terminal operations as separate activities, including cargo handling,
  cranes, yard tractors, terminal lighting, reefer plugs, gate operations,
  inspections, and administrative processing.
- Cargo consolidation, deconsolidation, warehousing, cross-docking, inventory
  holding, and stockout effects.
- Empty repositioning, backhaul imbalance, fleet scheduling, vessel rotation,
  and truck dispatch constraints.
- Detailed congestion, waiting time, port dwell time, berth availability, and
  weather-related delays.
- Refrigeration, cargo-specific packaging, cargo damage, insurance, security,
  and customs or tax treatment.
- Non-greenhouse-gas externalities such as local air pollutants, noise,
  accidents, road wear, land use, and ecosystem impacts.
- Demand response, modal market adoption, induced demand, and network-wide
  equilibrium effects.
- Upstream fuel production, refining, electricity generation, and distribution,
  unless the selected emission factors are explicitly documented as
  well-to-wheel factors.
- Financial costs that are not explicitly represented by the implemented cost
  model, such as inventory carrying cost, opportunity cost of time, contract
  penalties, and service reliability premiums.

Recommended wording:

> The model does not constitute a complete life-cycle assessment of freight
> transport. It excludes vehicle and infrastructure life cycles, detailed
> terminal operations, logistics network optimization, non-GHG externalities,
> and other indirect effects unless they are explicitly embedded in the
> documented factors used by the model.

## 5. Boundary Risks

The following risks should be acknowledged because they can affect interpretation
even when the computational model is internally consistent.

### 5.1 Asymmetric Inclusion Risk

If a component is included for one transport chain but omitted for the other,
the comparison may become biased. For example, adding port handling emissions to
the multimodal chain without adding comparable terminal or loading assumptions
for the road-only chain would change the meaning of the comparison.

Methodology debt:

- Confirm whether any cost or emissions factor already embeds terminal,
  handling, or administrative components.
- Avoid adding chain-specific components unless comparable treatment is possible
  for both alternatives or the asymmetry is explicitly justified.

### 5.2 Emission Factor Scope Risk

Emission factors may represent different scopes, such as tank-to-wheel,
well-to-tank, or well-to-wheel emissions. Mixing scopes can produce misleading
results.

Methodology debt:

- Document whether each fuel and mode emission factor is tank-to-wheel or
  well-to-wheel.
- If factor scopes differ, either harmonize them or state the limitation
  directly in the thesis.

### 5.3 Load Factor and Utilization Risk

Freight emissions and costs are sensitive to assumptions about payload,
utilization, empty return trips, and vehicle or vessel capacity. A model that
uses fixed payload assumptions should not be interpreted as a complete fleet
utilization model.

Methodology debt:

- State the load or cargo mass assumption used in each scenario.
- Clarify whether empty movements and backhauls are excluded or represented by
  aggregate factors.

### 5.4 Port Selection Risk

The nearest or modeled port may not be the commercially feasible port. Real
decisions may depend on service frequency, vessel availability, cargo type,
terminal capacity, contracts, regulatory constraints, and schedule reliability.

Methodology debt:

- Describe port selection as a scenario rule rather than as a proof of market
  optimality.
- Identify any cases where the selected port pair should be interpreted as
  illustrative rather than operationally definitive.

### 5.5 Temporal and Operational Variability Risk

The model may use static distances, costs, and factors, while real freight
operations vary over time. Fuel prices, tolls, congestion, vessel schedules,
weather, and port waiting times can materially change results.

Methodology debt:

- State the temporal validity of input factors where known.
- Avoid presenting a single model run as a permanent ranking between modes.

### 5.6 Spatial Resolution Risk

Coordinate precision and route provider behavior can affect road distance and
therefore emissions and costs. This is especially relevant when origin or
destination points represent municipalities, facilities, centroids, or
approximated coordinates.

Methodology debt:

- Explain the geographic resolution of origins and destinations.
- Note that route geometries are modeled representations, not audited GPS traces
  of actual trips.

### 5.7 Cost Boundary Risk

Cost comparisons can be narrower than logistics decision-making. A modeled
transport cost may exclude reliability, inventory, contractual, and service
quality effects that matter to shippers.

Methodology debt:

- State whether the cost model is intended to represent direct transport cost
  only.
- Avoid interpreting lower modeled cost as a complete measure of commercial
  attractiveness unless service-level factors are also modeled.

## 6. Recommended Thesis Wording

The thesis can use the following consolidated wording, adapted as needed to the
language and style of the final document:

> The analysis compares two alternative transport chains for the same freight
> demand: a road-only chain and a road-cabotage-road multimodal chain. The
> functional unit is the movement of a defined shipment, with fixed cargo mass,
> origin, and destination, within Brazil. The system boundary includes the
> operational transport activities explicitly represented by the model: road
> transport between origin and destination in the road-only alternative, road
> access and egress to selected ports in the multimodal alternative, and the
> domestic maritime cabotage movement between those ports. The comparison is
> based on modeled distances, fuel use, greenhouse-gas emissions, and transport
> costs where these quantities are calculated from documented formulas and
> traceable input data.
>
> The study should not be interpreted as a complete life-cycle assessment or as
> a full logistics network optimization. It excludes vehicle and infrastructure
> life cycles, detailed terminal operations, warehousing, inventory effects,
> empty repositioning, service reliability, non-GHG externalities, and broader
> market responses unless such elements are explicitly embedded in the factors
> used by the model. When a component is represented through an aggregate factor
> rather than modeled directly, this treatment is identified as a modeling
> assumption. Remaining uncertainties, especially emission factor scope, load
> factor treatment, port selection feasibility, and temporal variability of cost
> inputs, are treated as methodological limitations rather than as resolved
> facts.

For a more cautious limitations paragraph:

> Because the model focuses on operational transport-chain comparison, its
> results should be interpreted as scenario-based estimates rather than
> definitive measurements of all environmental and economic consequences of
> modal choice. The conclusions are strongest for the components explicitly
> modeled and weakest for components outside the boundary or represented only by
> aggregate assumptions.

