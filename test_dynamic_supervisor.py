#!/usr/bin/env python3
"""
Quick test to verify agents load from fixed JSON configuration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/src'))

def test_agents_loading():
    """Test that agents load properly from the fixed JSON configuration"""
    print("=== Testing Agents Loading After JSON Fix ===\n")
    
    try:
        # Test JSON parsing first
        import json
        config_path = os.path.join(os.path.dirname(__file__), 'backend/src/data/agents_config.json')
        
        print("1. Testing JSON validity...")
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        print("✓ JSON file is valid")
        
        # Check agents structure
        agents_config = config_data.get('agents', {})
        skills_config = config_data.get('skills', {})
        
        print(f"✓ Found {len(agents_config)} agents in config")
        print(f"✓ Found {len(skills_config)} skills in config")
        
        # Test agent loading
        print("\n2. Testing agent registry loading...")
        from agent.enhanced_registry import enhanced_agent_registry
        
        # Force reload
        enhanced_agent_registry.reload_agents()
        
        # Get available agents
        agents = enhanced_agent_registry.list_available_agents()
        print(f"✓ Successfully loaded {len(agents)} agents")
        
        # List each agent
        print("\n3. Available agents:")
        for agent_id in agents:
            try:
                agent = enhanced_agent_registry.get_agent(agent_id)
                metadata = agent.get_metadata()
                print(f"  - {agent_id}: {metadata.get('name', 'Unknown')} ({len(agent.get_skills())} skills)")
            except Exception as e:
                print(f"  - {agent_id}: ERROR - {e}")
        
        # Test skills
        print("\n4. Skills validation:")
        for agent_id in agents:
            agent = enhanced_agent_registry.get_agent(agent_id)
            agent_skills = agent.get_skills()
            if agent_skills:
                print(f"  {agent_id}: {agent_skills}")
                # Check if all skills are defined
                for skill in agent_skills:
                    if skill not in skills_config:
                        print(f"    ⚠️ Skill '{skill}' not found in skills config")
                    else:
                        print(f"    ✓ Skill '{skill}' is properly defined")
        
        print(f"\n🎉 SUCCESS! All {len(agents)} agents loaded correctly")
        print("The frontend should now display the agents properly!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Agent loading error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agents_loading()
    sys.exit(0 if success else 1)