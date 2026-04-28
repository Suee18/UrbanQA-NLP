# Munich Smart City Digital Twin

## Project overview

The Smart City Digital Twin is a system for procedural generation, real-time simulation, and visualisation of urban environments. It combines OpenStreetMap-derived 3D geometry, microscopic traffic simulation, an intelligent agent framework, and a natural-language question-answering interface in a single integrated platform. The prototype demonstration uses the Munich Klinikviertel district as its dataset.

## Scope and features

The system covers procedural geometry processing, microscopic traffic simulation, real-time visualisation, an agent framework, a virtual sensor layer, a unified dashboard interface, hazard simulation, runtime scenario generation, and a natural language interface backed by the UrbanQA question answering system.

Geometry processing performs procedural generation of 3D city geometry — buildings and roads — from OpenStreetMap data using SideFX Houdini, exported as Universal Scene Description (USD) assets. Traffic simulation uses SUMO for microscopic traffic simulation, including network generation, route computation, and real-time vehicle state extraction via TraCI. Real-time visualisation uses an Unreal Engine 5 environment with USD scene import, vehicle actor animation, and smooth interpolation at display frame rates.

The agent framework consists of four traffic monitoring agents: incident detection, congestion analysis, optimisation, and vehicle spawning. The agents stream events to the visualisation layer. The sensor layer includes virtual traffic sensors such as induction loops, speed detectors, and occupancy monitors for data collection.

The dashboard interface is a universal dashboard providing simulation status, agent feedback, sensor readings, notifications, camera controls, a hazard palette, scenario configuration, and UrbanQA query panels. Hazard simulation supports drag-and-drop hazard injection with visual indicators and observation of agent responses. Scenario generation allows runtime parameter adjustment of vehicle count, duration, speed limits, spawn rates, and random seed via bidirectional WebSocket communication. The natural language interface is the UrbanQA question answering system with passage retrieval and answer extraction for city-related queries. The prototype city is the Munich Klinikviertel district.

## System architecture

The Smart City Digital Twin system comprises five principal subsystems connected by open communication protocols.

The Geometry Processing Pipeline ingests OpenStreetMap XML data into a SideFX Houdini node graph, which filters, processes, and extrudes building footprints and road surfaces. The resulting geometry is exported as a Universal Scene Description USDA file with named primitive hierarchies under /World/buildings and /World/roads.

The Traffic Simulation Backend is a Python application that interfaces with the SUMO microscopic traffic simulator via TraCI. Vehicle positions, headings, and speeds are extracted at each simulation step and streamed over UDP at 60 Hz. A sensor layer collects data from virtual detectors distributed throughout the road network. A WebSocket server receives scenario parameters and UrbanQA queries from the dashboard.

The Real-Time Streaming Pipeline maintains consistent 60 Hz transmission rates regardless of simulation complexity. Vehicle state, sensor readings, and agent events are serialised into JSON packets and broadcast over UDP with minimal latency. This real-time pipeline ensures that the visualisation layer reflects simulation state within a single frame, enabling responsive user interaction and accurate temporal representation of traffic dynamics.

The Intelligent Agent Orchestration System employs a multi-agent architecture comprising four specialised agents: incident detection, congestion analysis, traffic optimisation, and dynamic vehicle spawning. These agents operate within a centralised orchestration framework that ensures coherent, non-conflicting behaviour across the system. Each agent maintains a shared state representation enabling uniform updates and synchronised decision-making. The orchestration layer resolves conflicts between agent recommendations, prevents overlapping responses to the same traffic condition, and guarantees consistent accuracy in behavioural outputs.

The Visualisation Environment is built on Unreal Engine 5. It loads the USD city geometry via the USD Stage Actor and applies material instances. Blueprint actors receive UDP packets, parse vehicle state, and animate SportsCar meshes with interpolated transforms. The universal dashboard provides simulation controls, agent feedback, sensor readings, hazard injection, and the UrbanQA query interface.

The UrbanQA NLP System is a retrieval-based question answering pipeline that processes natural language queries about the rendered city. The system uses BM25 sparse retrieval, dense semantic retrieval with mpnet embeddings stored in a FAISS index, and Reciprocal Rank Fusion (RRF) to combine the two. Top candidates are reranked with a cross-encoder. A transformer-based extractive reader (RoBERTa fine-tuned on SQuAD 2.0) extracts precise answer spans.

Communication between subsystems uses three protocols: UDP for high-frequency unidirectional vehicle state streaming, WebSocket for bidirectional control and query traffic, and TraCI over TCP for simulation control. All payloads are serialised as JSON, ensuring human readability and straightforward debugging.

## Stakeholders and users

The system addresses three primary stakeholder groups. Municipal Governments use the system to visualise traffic patterns, evaluate infrastructure investments, and plan responses to incidents or special events. The system's open architecture eliminates vendor lock-in and reduces total cost of ownership compared to commercial alternatives such as Bentley iTwin or NVIDIA Omniverse. Urban Planning Agencies use the system to test hypothetical scenarios such as road closures, new developments, and traffic calming measures before committing resources. The hazard injection and scenario generation features support rapid what-if analysis. Research Institutions studying traffic flow, agent-based modelling, or urban informatics benefit from the open-source codebase, documented APIs, and modular architecture.

The system supports users with varying technical expertise. Traffic Engineers and Urban Planners are domain experts with limited programming experience who interact primarily through the dashboard, adjusting scenario parameters, injecting hazards, and reviewing agent feedback. No coding is required for standard operations. GIS Analysts are users familiar with geospatial data formats and OpenStreetMap who may prepare custom OSM extracts for new cities or modify the Houdini pipeline. Software Developers and Researchers extend the agent framework, implement new agents, modify the NLP pipeline, or integrate alternative simulation backends via the documented UDP and WebSocket interfaces. Decision Makers are executives and policymakers who consume visualisation outputs and agent reports without direct system interaction; the UrbanQA natural language interface enables them to query city information without technical training.

## Dashboard interface

The dashboard provides a unified control surface for simulation monitoring, configuration, and analysis. The interface is implemented using Unreal Motion Graphics widgets overlaid on the 3D viewport. The design follows four principles: non-intrusive overlays where control panels slide in from screen edges to preserve viewport visibility; progressive disclosure with primary status always visible in the Top Bar and detailed controls in Left Panel tabs; immediate feedback where all user actions produce visual confirmation via Notification Toasts; and separation of concerns where agent-generated alerts appear in the Alert Stack and system notifications appear as Toasts.

The dashboard supports three primary interaction modes selectable via Left Panel navigation tabs. Scenario Mode lets users configure simulation parameters including vehicle count, duration, spawn rate, speed limits, and random seed. It allows placing and removing traffic hazards via drag-and-drop and applying preset configurations for common scenarios. Analytics Mode lets users monitor real-time simulation metrics, view agent status and event logs, and inspect sensor readings from virtual induction loops and speed detectors. AI Mode lets users submit natural language queries about the simulated city via the UrbanQA interface. Responses include confidence scores and source citations and a query history for repeated analysis.

Persistent interface elements include the Top Bar showing connection status, simulation time, vehicle count, step number, and playback state; a Menu Toggle for the Left Panel; the Alert Stack for agent-generated notifications; the Camera HUD with camera switching, directional panning, and zoom controls; and Notification Toasts displayed at the top-left of the screen for transient system messages.

The Scenario panel provides controls for vehicle count (1 to 200), duration in seconds, spawn rate in vehicles per minute, speed limit in km/h, and a random seed control with a randomise button. A preset dropdown offers configurations such as Rush Hour. A draggable hazard palette includes Closure, Accident, Construction, and Weather hazards. An active hazards list shows currently placed hazards with remove buttons. Apply and Reset buttons commit or revert changes.

The Analytics panel displays simulation metrics such as total distance, average speed, active vehicles, completed trips, and collisions. Agent status cards show event counts and the most recent event type for each agent. A scrollable event log shows timestamped entries categorised as INFO, WARN, or CRIT.

The AI panel contains the UrbanQA natural language query interface. It includes a query input field, a response area showing the answer with a confidence score and source citation such as "munich_wiki_p42", a query history list with re-execute buttons, and a clear history control.

## Geometry processing implementation

The geometry processing stage is implemented in SideFX Houdini 21.0.512 by constructing an eight-node SOP graph inside a geometry object context named geo_city. The pipeline ingests the raw MunichSmall.osm file, filters the relevant geometric primitives, generates 3D road and building geometry in parallel branches, applies naming attributes for USD primitive separation, merges the outputs into a unified scene, and exports the result as a USDA asset.

The pipeline incorporates two Name SOP nodes (name_roads and name1) that assign a name primitive attribute to each geometry category. This attribute is read by the USD File Export ROP during kind authoring, enabling the exporter to generate separate USD prims for roads and buildings rather than merging all geometry into a single mesh. The resulting prim hierarchy uses /World/buildings for all building geometry and /World/roads_0 for all road geometry. This separation enables drag-and-drop material assignment in Unreal Engine's USD Stage Editor, as each category exists as an independent selectable mesh.

The USD File Export ROP (usdexport1) was configured with Nested groups and components kind authoring, relative paths enabled, and Houdini-specific custom data cleared, ensuring the resulting USDA file is portable and compatible with Unreal Engine 5's USD Stage Editor without further modification.

## USD scene import into Unreal Engine 5

The USDA scene asset produced by the Houdini pipeline is loaded into Unreal Engine 5 via the USD Stage Editor workflow. Upon opening the USD Stage Editor through Windows then USD Stage Editor and loading the USDA file, Unreal Engine automatically instantiates a USD Stage Actor in the active level. The USD Stage Actor renders the scene transiently by interpreting the USD primitive hierarchy at runtime rather than converting primitives into persistent Unreal assets. This non-destructive approach preserves the original file structure and allows modifications to the source USDA to be reflected without re-importing.

The scene geometry is represented as separate mesh prims: /World/buildings for building volumes and /World/roads_0 for road surfaces. This separation enables independent material assignment for each category within the USD Stage Editor.

Materials are assigned by dragging Unreal material assets onto mesh prims in the USD Stage Editor. Unreal Engine creates UnrealMaterial and UnrealShader prims referencing the material asset path. These assignments are stored in a session layer rather than modifying the source file. The source layer is the original USDA file exported from Houdini, treated as read-only during editing. The session layer is a temporary layer storing material bindings and edits made within Unreal Engine. This workflow allows the Houdini pipeline to regenerate geometry without losing material assignments. The session layer can be exported to permanently bake bindings if required.

Two material instances provide visual differentiation between geometry categories. MI_MarbleWhite is applied to /World/buildings, providing a clean architectural appearance for building volumes. MI_Asphalt is applied to /World/roads_0, representing road surface texture. Both inherit from the M_MS_Srf parent material, exposing parameter groups for Base Color, Specular, ORM (Occlusion/Roughness/Metallic), Normal, and Displacement.

## Traffic simulation backend

The traffic simulation backend is a modular Python application comprising six primary modules. The system requires Python 3.10 or later and depends on the SUMO traffic simulation suite for simulation and route generation.

The core modules are: main.py, the entry point that handles CLI argument parsing and orchestration; config.py, a configuration dataclass with simulation parameters; sumo_simulator.py, which manages SUMO lifecycle, TraCI queries, and coordinate transforms; udp_streamer.py, which performs JSON serialisation, UDP broadcast, and rate limiting; protocol.py, which defines the VehicleState dataclass; sumo_network_generator.py for route generation and SUMO config file creation; and usda_parser.py for USDA bounds extraction and offset computation.

The agent framework modules include agents/__init__.py for package exports, agents/base_agent.py defining the BaseAgent class and AgentEvent dataclass, agents/agent_manager.py for the AgentManager orchestrator, and agents/incident_detector.py for the IncidentDetector concrete agent. Test utilities include test_receiver.py, a UDP receiver for debugging without Unreal Engine, and test_agents.py, the agent framework unit tests.

The simulation is launched via the command line. A typical invocation for the Munich dataset uses python main.py with arguments --usda MunichSmall.usda, --net sumo_files/city.net.xml, --vehicles 20, --duration 300, --offset -233646 -503309 0, and --sumo-binary sumo-gui. The --sumo-binary sumo-gui flag launches SUMO with its graphical interface for visual verification during development. For headless operation, the sumo binary is used instead.

## UDP streaming protocol

Vehicle state is transmitted to Unreal Engine as JSON-encoded UDP datagrams at a rate of 60 Hz. Each datagram contains a batch of vehicle records along with simulation metadata. The JSON schema includes a t field for simulation time in seconds (float), a step field for the frame counter (int), a units field that is always "cm" for coordinate units, and a vehicles array. Each vehicle record contains an id (string), x/y/z coordinates in centimetres (float), yaw_deg for heading in degrees (float), and speed in cm/s (float).

For frames exceeding the UDP safe payload limit of 60,000 bytes, the vehicle list is partitioned into chunks of 200 vehicles each. Chunked frames include additional fields chunk (zero-indexed chunk number) and chunks (total chunk count) to enable reassembly on the receiver side.

Control events are transmitted as single-field JSON objects such as {"t": 0.0, "event": "start"} and {"t": 300.0, "event": "stop"}.

## SUMO network and route files

The SUMO simulation requires three input files. The network file city.net.xml is the road network, generated one time from the source OSM data using SUMO's netconvert utility, and is not regenerated during normal operation. The route file city.rou.xml contains vehicle routes generated per-run by randomTrips.py and duarouter. The simulation configuration file simulation.sumocfg is generated per-run by the backend.

## Agent framework architecture

The traffic simulation backend implements an extensible agent framework that enables real-time analysis of vehicle behaviour during simulation. Agents receive the complete vehicle state list on every simulation tick and may emit structured events that are broadcast alongside vehicle positions in the UDP stream.

The framework follows a plugin architecture with three core components. BaseAgent is an abstract base class defining the agent lifecycle through on_start and on_stop methods, and the process method that subclasses must implement. It provides an emit factory method for creating events. AgentEvent is a dataclass representing a structured event with fields for agent name, event type, message, affected vehicle, severity level, coordinates, and arbitrary additional data. AgentManager is an orchestrator that maintains a registry of agents, invokes their process methods each tick, and aggregates emitted events.

The agent framework is integrated into sumo_simulator.py via four steps: importing AgentManager and IncidentDetector from agents, initialising them in SUMOSimulator __init__, ticking the agent_manager in the simulation loop after building vehicle_list, and managing lifecycle with start before the loop and stop after.

New agents are created by subclassing BaseAgent and implementing the process method which receives vehicles, sim_time, and step. The vehicle list contains fields id, x, y, z, yaw_deg, and speed in Unreal centimetres. The method returns a list of AgentEvent objects. Multiple agents may be registered simultaneously; their events are aggregated into a single events array in the UDP packet.

## Adaptive Spawner Agent

The Adaptive Spawner Agent is a concrete class extending BaseAgent and integrated into the simulation backend. The agent executes during each simulation tick and performs density evaluation at configurable intervals. The implementation follows the agent lifecycle: Initialization, Tick, Process, Decision, Action, Event Emission.

During initialization, the agent loads configuration parameters and prepares internal state variables including density thresholds, batch sizes, intervals, history buffers, and a spawned vehicle registry. The class is initialised with min_vehicles, max_vehicles, and batch_size parameters.

The AgentManager invokes the agent at each simulation step via agent_manager.tick(vehicle_list, sim_time, step). The Adaptive Spawner Agent receives vehicle_list, simulation time, and the step counter. The agent executes only when check_interval is reached.

Density measurement uses traci.vehicle.getIDList() to compute current_density, which is appended to history. If density falls below min_vehicles, the agent spawns a batch of vehicles by selecting a random route, creating a unique vehicle ID, adding the vehicle using TraCI, registering it in the spawned set, and emitting a spawn event. If density exceeds max_vehicles, the agent removes dynamically spawned vehicles first via traci.vehicle.remove. Removal ensures no static vehicle deletion, stable traffic flow, and controlled density reduction.

At the analytics interval, the agent computes average density, minimum density, and maximum density, then emits a density event. The agent returns structured AgentEvent objects with type "spawn" or similar, which are aggregated by AgentManager and forwarded to the simulation output pipeline.

The Adaptive Spawner Agent is registered in the simulator with min_vehicles=10 and max_vehicles=30 by default. Execution flow proceeds: Simulation Step, AgentManager.tick, AdaptiveSpawner.process, Spawn or Remove decisions, Events returned, UDP stream updated.

The implementation enforces safety constraints: removal only of dynamic vehicles, bounded spawn count, interval-based evaluation, deterministic decision logic, and non-blocking TraCI calls. These maintain simulation stability. The result is a traffic population controller ensuring continuous simulation, realistic traffic density, stable performance, and modular AI agent integration.

## Congestion Prediction Agent

The Congestion Prediction Agent is a BaseAgent subclass that performs time-series forecasting on traffic data at fixed intervals. The agent collects historical data, prepares features, executes ML inference, and emits prediction events. The workflow is: Initialization, Data Collection, Feature Creation, Prediction, Classification, Event Emission.

The agent loads model and configuration. Initialization includes a prediction horizon, model selection, history buffers, thresholds, and feature extractors. The class takes model and horizon parameters.

The agent collects traffic metrics from SUMO using traci.edge.getLastStepVehicleNumber for vehicle_count and traci.edge.getLastStepMeanSpeed for avg_speed. Data is appended to history per edge.

The agent converts history to model input. Example features include the last 60 density values, speed trend, moving average, and variance. Model inference supports three options: LSTM prediction, regression prediction, or time-series ARIMA forecast. Output is the predicted density for the next horizon.

Prediction is converted to congestion levels: if prediction exceeds overload_threshold, level is "overload"; if it exceeds congestion_threshold, level is "high". Spike detection compares delta = prediction - current_density against a spike_threshold and emits a spike event if exceeded.

The agent emits structured events with type "congestion_prediction". To maintain real-time performance, prediction runs at intervals, with a lightweight regression fallback, a bounded history window, and cached model inference. Complexity is O(n roads). Safety constraints ensure prediction only occurs after sufficient history, model fallback is supported, memory usage is bounded, and inference is non-blocking.

The Congestion Prediction Agent provides future traffic awareness, proactive congestion detection, AI-ready traffic forecasting, and predictive smart city intelligence.

## Emergency Vehicle Priority Agent

The Emergency Vehicle Priority Agent is a BaseAgent subclass that monitors vehicles, detects emergency types, computes a priority corridor, overrides traffic signals, and clears lanes. The workflow is: Initialization, Detection, Route Analysis, Signal Override, Lane Clearing, Event Emission.

The agent loads configuration and initializes state. Initialization includes emergency types, detection radius, override duration, and an active emergency registry. The agent maintains active_emergencies and controlled_signals dictionaries.

AgentManager calls the agent every simulation step. The agent scans vehicles using vehicle type check, ID prefix check, and class check. If a vehicle is emergency, it is registered.

The agent retrieves the vehicle route via traci.vehicle.getRoute(vehicle_id). Next intersections are extracted natively. The agent identifies upcoming traffic light systems (TLS) and marks them for override.

Signal override sets green lights for the emergency vehicle route and red for conflicting directions. Green phase is simultaneously extended via traci.trafficlight.setRedYellowGreenState. Lane clearance slows vehicles ahead via traci.vehicle.slowDown or enforces lane changes via traci.vehicle.changeLane. Optional stop enforcement uses traci.vehicle.setStop.

The emergency vehicle is artificially given speed priority via traci.vehicle.setSpeedFactor with a factor of 1.2. The agent emits operational events such as type "signal_override". The agent maintains the green corridor while the emergency vehicle is active. When the vehicle exits, the agent restores signals, removes overrides, and clears state.

Performance considerations: limited to emergency vehicles only, intersection-based control, event-driven updates, minimal TraCI calls. Complexity is O(n vehicles). Safety constraints include restoring signals after completion, overriding only required intersections, bounded detection radius, avoiding infinite green states, and preventing deadlocks.

The Emergency Vehicle Priority Agent provides emergency traffic control, intelligent signal override, realistic smart city behaviour, an impressive demo scenario, and reduced emergency response time.

## Unreal Engine integration

The Unreal Engine 5 integration layer receives vehicle state data from the Python simulation backend via UDP and renders the traffic simulation in real-time within the digital twin environment. The implementation comprises three Blueprint actors and three supporting data structures organised in a pipeline architecture that separates network communication, data management, and visual representation.

The Blueprint system follows a three-tier architecture. BP_UDPReceiver listens on UDP port 5005, receives raw byte payloads, parses JSON into structured data, dispatches vehicle states to the traffic bridge, and handles agent event notifications. BP_SumoTrafficBridge maintains a map of vehicle states indexed by vehicle ID, converts parsed JSON data into Unreal-native types (Vector, Rotator), and updates vehicle actor target transforms each frame. SportsCar is a static mesh actor representing a single vehicle, which interpolates smoothly toward its target position and rotation each tick.

Data flows unidirectionally through the pipeline: UDP bytes arrive at BP_UDPReceiver, are parsed into S_PacketData structures, passed to BP_SumoTrafficBridge for conversion to ST_SumoVehicleState, and finally applied to SportsCar actors as interpolation targets.

## Blueprint data structures

Three Blueprint structures mirror the JSON payload format emitted by the Python backend. S_PacketData has fields t (Float, JSON "t"), step (Integer, JSON "step"), units (String, JSON "units"), and vehicles (Array of S_VehicleData, JSON "vehicles"). S_VehicleData has fields id (String), x (Float), y (Float), z (Float), yaw_deg (Float), and speed (Float). ST_SumoVehicleState has Position (Vector, derived from x/y/z), Rotation (Rotator, derived from yaw_deg), Speed (Float, direct copy), and VehicleID (String, direct copy).

The S_PacketData and S_VehicleData structures directly mirror the JSON schema, enabling automatic deserialisation via the SocketIOClient plugin's Json Object to Struct node. The ST_SumoVehicleState structure represents the processed vehicle state using Unreal-native types suitable for direct application to actor transforms.

## UDP Receiver Blueprint

The BP_UDPReceiver Blueprint is responsible for network communication, JSON parsing, and event dispatch. The Blueprint contains a single UDP component configured with: Send IP 127.0.0.1, Send Port 5005, Receive Port 5005, Buffer Size 2097152 (2 MB), Should Auto Open Receive enabled, and Receive Socket Name "ue4-dgram-receive".

The Blueprint implements three event graph flows. The BeginPlay flow opens a receive socket on port 5005, stores the socket reference, prints a confirmation message, creates an instance of the WBP_IncidentAlert widget, and adds it to the viewport for displaying agent notifications.

The On Received Bytes flow fires when UDP data arrives with the raw byte array, source IP address, and port number. The byte array is converted to a string via the To String (Bytes) node and stored in the RawStringFromSUMO variable.

The Event Tick flow parses the stored JSON string each frame: Construct Json Object creates a parser, Decode Json parses RawStringFromSUMO, Json Object to Struct deserialises into S_PacketData, the parsed data is stored in LatestPacketData, Update Traffic from Packet is called on BP_SumoTrafficBridge, and a parallel branch checks for an "events" field. If events exist, Get Array Field retrieves the events array, which is iterated via For Each Loop. Each event is parsed for type, msg, severity, and vehicle fields. A Switch on String node routes events by type: congestion, stopped, cluster, or recovered, triggering Show Alert or Hide Alert calls on the widget.

## Traffic Bridge Blueprint

The BP_SumoTrafficBridge Blueprint serves as the central data manager. It has variables: SumoVehiclesMap (Map from String to ST_SumoVehicleState) for vehicle state storage, Sumo (Boolean) for connection status, MapOffset_X (Float) for X-axis coordinate adjustment, and MapOffset_Y (Float) for Y-axis coordinate adjustment.

The UpdateTrafficFromPacket custom event is called by BP_UDPReceiver with the parsed S_PacketData. It clears SumoVehiclesMap, breaks S_PacketData to extract the vehicles array, iterates with For Each Loop, breaks S_VehicleData to get id and position fields, makes a Vector from x/y/z, makes a Rotator with Roll=0 Pitch=0 Yaw=yaw_deg, constructs ST_SumoVehicleState, and adds it to SumoVehiclesMap keyed by vehicle ID.

The Event Tick flow updates all vehicle actors each frame: Get All Actors Of Class retrieves all SportsCar actors, For Each Loop iterates them, the actor's MySumoID variable is read, Find looks up the ID in SumoVehiclesMap, Branch checks if found, Break ST_SumoVehicleState extracts position and rotation, Break Vector decomposes position into X/Y/Z, MapOffset_X and MapOffset_Y are added for fine-tuning alignment, Make Vector reconstructs the adjusted position, and Set Target Location and Set Target Rotator update the actor's target variables.

## Vehicle Actor Blueprint

The SportsCar Blueprint represents a single simulated vehicle. Each instance is pre-placed in the level at the origin (0, 0, 0) with a manually assigned MySumoID corresponding to a SUMO vehicle identifier. Its variables are MySumoID (String, the vehicle identifier matching SUMO ID), TargetLocation (Vector, interpolation target position), and TargetRotator (Rotator, interpolation target rotation).

The Blueprint contains a StaticMesh component using a vehicle model from the Vehicle Variety Pack asset. The Event Tick flow implements smooth interpolation toward the target transform: Get Actor Location retrieves current position, VInterp To interpolates toward TargetLocation using Delta Time and an interpolation speed of 10.0, Set Actor Location applies the interpolated position with Teleport enabled, Get Actor Rotation retrieves current rotation, RInterp To interpolates toward TargetRotator using Delta Time and an interpolation speed of 6.0, and Set Actor Rotation applies the interpolated rotation with Teleport Physics enabled.

The differing interpolation speeds — 10.0 for position and 6.0 for rotation — provide responsive position tracking while maintaining smooth rotational movement, avoiding visual jitter during direction changes.
