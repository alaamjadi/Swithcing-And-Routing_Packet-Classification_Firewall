import network_utils as nu

"""
Container for binary tree nodes
"""
class Node(object):
    value = None # used for debugging
    zero = None # zero child
    one = None # one child
    dst_root = None # If this node has sub-tier this field will contain its root refference
    end = False # True if any rules finished here, False otherwise
    rules = None
    
    def __init__(self, value="^", end=False):
        self.value = value
        self.end = end
        if self.end:
            self.rules = []

"""
This Method add second-tier nodes to the tree recursively
"""
def add_dst_nodes(node, rule, index, rule_index):
    # reach end of the second-tier add rules
    if len(rule) <= index :
        if node.zero is None: # we don't have a new node
            node.zero = Node("$",end=True)
            
        if not node.zero.end :
            node.zero.end = True
            node.zero.rules = []
        
        node.zero.rules.append(rule_index)
        
        return # miyad birun, mire too main
    
    # Add zero child
    if rule[index] == "0":
        if node.zero is None:
            node.zero = Node(value=(node.value + "0"))
        add_dst_nodes(node.zero,rule, index+1, rule_index)
    # Add one child
    else :
        if node.one is None:
            node.one = Node(value=(node.value + "1"))
        add_dst_nodes(node.one,rule, index+1, rule_index)

"""
This Method add first-tier nodes to the tree recursively
"""
def add_src_nodes(node, rule, index, dst_rule, rule_index):
    # in case of src_sub='*' this block will execut
    if rule is None:
        rule=[]
    
    # 
    if len(rule) <= index :
        # in case of src_sub=10.0.0.0/24 dst_sub = '*' or src_sub='*' dst_sub = '10.0.0.0/24' or src_sub='*' dst_sub = '*'
        # this block will execute as well
        if dst_rule is None:
            if not node.end: # if we have match
                node.rules = []

            node.end = True
            node.rules.append(rule_index) 
            return
        
        # add next-trie root to the tree
        if node.dst_root is None:
            node.dst_root = Node(value="#") # root of the 2nd triangle
        
        add_dst_nodes(node.dst_root, dst_rule, 0, rule_index) # create 2nd triangle
        return
    
    # add zero child recursive
    if rule[index] == "0":
        if node.zero is None:
            node.zero = Node(value=(node.value + "0"))
        add_src_nodes(node.zero,rule, index+1, dst_rule, rule_index)
    # add one child recursive
    else :
        if node.one is None:
            node.one = Node(value=(node.value + "1"))
        add_src_nodes(node.one,rule, index+1, dst_rule, rule_index)
        

"""
Depict the tree
"""
def show(root, indent="", has_zero=False):

    last_indent = "|--"
    if has_zero:
        last_indent = "--"
    elif root.value == "^":
        indent = ""
        last_indent = ""

    if not root.end:
        print("%s%svalue = %s" % (indent, last_indent, root.value))
    else:
        print("%s%svalue = %s, rules: %s" % (indent, last_indent, root.value, root.rules))

    if root.one is not None:
        if root.zero is None:
            show(root.one, indent + "   ")
        else:
            show(root.one, indent + "  |", True)
    if root.zero is not None:
        if root.dst_root is None:
            show(root.zero, indent + "  ")
        else:
            show(root.zero, indent + "  |", True)
    if root.dst_root is not None:
        show(root.dst_root, indent + "  ")
        
        
def match_dst(node, dst_bin, dst_index, actions):
    if node.end :
        actions.extend(node.rules)
        # we should not return otherwise we can gave more end
    
    if dst_index >= 32: # if it's 32bits
        if node.zero.value == "$": #match final
            actions.extend(node.zero.rules) #rules added
        return
    
    if node.zero is not None and dst_bin[dst_index] == "0":
        match_dst(node.zero, dst_bin, dst_index+1, actions)
        return
    if node.one is not None and dst_bin[dst_index] == "1":
        match_dst(node.one, dst_bin, dst_index+1, actions)
        return
    
    return


def match(node, src_bin, src_index, dst_bin, dst_index, actions):
    if node.end :
        actions.extend(node.rules) #rules=[1,2] > [1,2,3]
    
    #If src_incoming_IP matched with src_rule > 2nd tier
    if node.dst_root is not None:
        match_dst(node.dst_root, dst_bin, dst_index, actions)
    
    # we start from root, the root have 0, src_incoming_packet=0
    # we have rule in zero
    if node.zero is not None and src_bin[src_index] == "0":
        match(node.zero, src_bin, src_index+1, dst_bin, dst_index, actions)
        return
    if node.one is not None and src_bin[src_index] == "1":
        match(node.one, src_bin, src_index+1, dst_bin, dst_index, actions)
        return
    
    return

def get_packets_actions(root, packets, rules, debug):
    actions=[]

    for packet in packets:
        candidate_actions = []
        match(root, packet.src_binary, 0, packet.dst_binary, 0, candidate_actions)

        final_actions = []

        for i in candidate_actions:
            if rules[i].protocol != '*' and rules[i].protocol != packet.protocol:
                continue
            if not nu.is_in_port_range(rules[i].src_port, packet.src_port):
                continue
            if not nu.is_in_port_range(rules[i].dst_port, packet.dst_port):
                continue
            final_actions.append(i)
        
       """  if debug:
            print(final_actions)
            print("action picked: " + str(sorted(final_actions)[0])) """
        actions.append(rules[sorted(final_actions)[0]].action)
        final_rule = rules[sorted(final_actions)[0]]
        print("Packet %s matched with %s action: %s " % (packet.src_ip, final_rule.src_sub, final_rule.action))

    return actions