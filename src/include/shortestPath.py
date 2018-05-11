import queue

MAX_INT = 1e10

def SPFA(graph, src):
    '''
    input: 
        graph: a list of list, adjacent table
        src: an integer(base 0), the source node
    output: 
        a list, the ith item is the distance from src to i
    '''
    V = len(graph)
    min_distance = [MAX_INT for i in range(V)]
    min_distance[src] = 0

    q = queue.Queue()
    q.put(src)
    while not q.empty():
        node = q.get()
        for destination, weight in enumerate(graph[node]):
            if weight < 0:
                break
            if min_distance[destination] > min_distance[node] + weight:
                min_distance[destination] = min_distance[node] + weight
                q.put(destination)
    
    return min_distance


if __name__ == "__main__":
    g = [
        [0, 1, MAX_INT, 3, MAX_INT, 1],
        [1, 0, 2, MAX_INT, MAX_INT, 2],
        [MAX_INT, 2, 0, 1, 2, MAX_INT],
        [3, MAX_INT, 1, 0, 2, MAX_INT],
        [MAX_INT, MAX_INT, 2, 2, 0, 2],
        [1, 2, MAX_INT, MAX_INT, 2, 0]
    ]    
    print(SPFA(g, 0))