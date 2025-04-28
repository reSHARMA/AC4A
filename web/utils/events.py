from web.agent.agent_manager import agent_manager
from src.utils.attribute_tree import AttributeTree
from web.utils.socket_io import init_socketio
import logging

logger = logging.getLogger(__name__)

# Get the socketio instance
socketio = init_socketio(None)  # We'll initialize it properly in app.py

def emit_policy_update():
    """Emit policy update to all connected clients"""
    try:
        logger.info("Emitting policy update to all connected clients")
        
        # Get attribute trees
        attribute_trees = agent_manager.get_attribute_trees()
        
        # Process trees into a format suitable for UI display
        def process_tree(tree):
            if not isinstance(tree, AttributeTree):
                logger.warning(f"Found non-AttributeTree object: {type(tree)}")
                return {"label": str(tree), "value": str(tree), "children": [], "access": "", "position": "", "positionValue": 0}
            
            key, value = list(tree.value.items())[0]
            node = {
                "label": key, 
                "value": value, 
                "children": [],
                "access": getattr(tree, 'access', ''),
                "position": getattr(tree, 'position', ''),
                "positionValue": getattr(tree, 'positionValue', 0)
            }
            
            for child in tree.children:
                node["children"].append(process_tree(child))
            
            return node
        
        # Process each tree in granular_data
        processed_trees = []
        seen_keys = set()
        
        for tree in attribute_trees:
            if isinstance(tree, AttributeTree):
                key, _ = list(tree.value.items())[0]
                if key not in seen_keys:
                    seen_keys.add(key)
                    processed_tree = process_tree(tree)
                    processed_trees.append(processed_tree)
                    logger.info(f"Added unique processed tree: {key}")
                else:
                    logger.info(f"Skipping duplicate processed tree: {key}")
            else:
                processed_tree = process_tree(tree)
                processed_trees.append(processed_tree)
        
        # Get policies
        policies = agent_manager.policy_system.policy_rules
        
        # Emit the update
        socketio.emit('policy_update', {
            "attribute_trees": processed_trees,
            "policies": policies
        })
        
        logger.info("Policy update emitted successfully")
    except Exception as e:
        logger.error(f"Error emitting policy update: {str(e)}", exc_info=True)