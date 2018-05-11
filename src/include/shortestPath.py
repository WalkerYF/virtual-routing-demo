import queue
import logging

MAX_INT = 1e10

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

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
    logger.info('src is ' + str(src))
    q.put(src)
    while not q.empty():
        node = q.get()
        logger.info('in %d' % node)
        for destination, weight in enumerate(graph[node]):
            logger.info('d {}, w {}'.format(str(destination), str(weight)))
            if weight < 0:
                continue
            if min_distance[destination] > min_distance[node] + weight:
                logger.info('update %d' % destination)
                min_distance[destination] = min_distance[node] + weight
                q.put(destination)
    
    replace_max_int_to_m1(min_distance)
    return min_distance

def replace_max_int_to_m1(ls):
    for idx, val in enumerate(ls):
        if val == MAX_INT:
            ls[idx] = -1


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