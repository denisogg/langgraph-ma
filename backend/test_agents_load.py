import sys
sys.path.append('src')
try:
    from agent.enhanced_registry import enhanced_agent_registry
    print('✅ Registry loaded successfully')
    agents = enhanced_agent_registry.list_available_agents() 
    print(f'✅ Available agents: {agents}')
    print(f'✅ Total agents: {len(agents)}')
    
    # Test the supervisor
    from agent.supervisor.enhanced_supervisor import EnhancedSupervisor
    supervisor = EnhancedSupervisor(agents, {})
    plan = supervisor.analyze_query('make me an analysis about weather and let granny tell me about it')
    print(f'✅ Multi-agent detection: {plan.requires_multi_agent}')
    print(f'✅ Agent sequence: {plan.agent_sequence}')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()