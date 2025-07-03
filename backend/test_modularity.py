from src.agent.enhanced_registry import enhanced_agent_registry

print('=== CHECKING AGENT REGISTRY ===')
print()

print('Available agents:')
agents = enhanced_agent_registry.list_available_agents()
print(f'Total: {len(agents)}')
for agent_id in agents:
    agent = enhanced_agent_registry.get_agent(agent_id)
    print(f'  - {agent_id}: {agent.get_name()}')

print()
print('Testing API-compatible format:')
metadata = enhanced_agent_registry.list_all_agents_metadata()
print(f'Metadata count: {len(metadata)}')
for meta in metadata:
    print(f'  - {meta[\"id\"]}: {meta[\"name\"]} (caps: {len(meta[\"capabilities\"])}, skills: {len(meta[\"skills\"])})')