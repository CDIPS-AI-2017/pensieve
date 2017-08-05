import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import pylab
import pensieve
from collections import Counter
import math

class Graph(object):
    G = None
    book = None
    def __init__(self, book=None):
        self.book = book
        self.G = nx.Graph()
    
    def max_degree(self):
        max_deg = 0
        for node in self.G.nodes():
            if self.G.degree(node) > max_deg:
                max_deg = self.G.degree(node)
        return max_deg
    
    def create_graph(self,n):
        list_of_people = Counter(self.book.words['people'])
        list_of_people = dict(list_of_people.most_common(n))
        for key in list_of_people.keys():
            self.G.add_node(key, weight=list_of_people[key])
        for i in range(len(self.book.paragraphs)):
            para_ppl = self.book.paragraphs[i].build_words_dict()['people']
            for person1 in para_ppl.keys():
                if person1 in list_of_people.keys():
                    for person2 in para_ppl.keys():
                        if person2 in list_of_people.keys() and person2 != person1:
                            w = para_ppl[person1] + para_ppl[person2]
                            if (person1,person2) in self.G.edges() or (person2,person1) in self.G.edges():
                                self.G[person1][person2]['weight'] += w
                            else:
                                self.G.add_edge(person1,person2,weight=w,thickness=1)
        print(list_of_people)
        
    def set_weights(self):
        for edge in self.G.edges(data = True):
            p1 = (edge[2]['weight']/self.G.node[edge[0]]['weight'])
            p2 = (edge[2]['weight']/self.G.node[edge[1]]['weight'])
            edge[2]['weight'] = max(p1*math.pow(p2,0.8),p2*math.pow(p1,0.8))
            edge[2]['thickness'] = math.sqrt(edge[2]['weight'])
    
    def graph(self):
        self.set_weights()
        pos=nx.spring_layout(self.G)
        
        edge_colors = ['blue' for edge in self.G.edges()]
        edge_widths = [d['thickness'] for u,v,d in self.G.edges(data=True)]
        
        nx.draw_networkx_edges(self.G, pos, width=edge_widths, edge_color=edge_colors)
        
        node_sizes = [100+50*self.G.degree(node) for node in self.G.nodes()]
        node_colors = [self.G.degree(node)/self.max_degree() for node in self.G.nodes()]
        node_labels = {node[0]:node[0] for node in self.G.nodes(data=True)}
        
        nx.draw_networkx_nodes(self.G, pos,node_color = node_colors, node_size=node_sizes, node_shape='h', cmap=plt.get_cmap('GnBu'),vmin=0,vmax=1, linewidths=5)
        nx.draw_networkx_labels(self.G, pos, labels=node_labels)
        
        plt.axis('off')
        pylab.show()
     