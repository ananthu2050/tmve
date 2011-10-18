import sys
import math
import sqlite3
import numpy as np


### score functions ###

#NOTE: what distance function is this?
def get_doc_score(doca, docb, axis=1):
    return .5 * np.sum((doca - docb)**2, axis=axis)

def get_topic_score(topica, topicb):
    score = 0
    total = math.pow(abs(math.sqrt(100) - math.sqrt(0)), 2) * len(topica)
    for term_id in range(len(topica)):
        thetaa = abs(topica[term_id])
        thetab = abs(topicb[term_id])
        score += math.pow(abs(math.sqrt(thetaa) - math.sqrt(thetab)), 2)
    return 0.5 * score / total

def get_term_score(terma, termb):
    score = 0
    for term_id in range(len(terma)):
        score += math.pow(terma[term_id] - termb[term_id], 2)
    return score


### write relations to db functions ###

def write_doc_doc(con, cur, gamma_file):
    cur.execute('CREATE TABLE doc_doc (id INTEGER PRIMARY KEY, doc_a INTEGER, doc_b INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX doc_doc_idx1 ON doc_doc(doc_a)')
    cur.execute('CREATE INDEX doc_doc_idx2 ON doc_doc(doc_b)')
    con.commit()

    docs = np.loadtxt(gamma_file) ** 2

    # get the closest 100 relations per document
    # NOTE: this is buggy, consider this case
    # you can't have multiple keys with the same value even if they exist
    for a in range(len(docs)):
        doc = docs[a]
        distance = get_doc_score(doc, docs)
        # drop zeros
        distance[distance == 0] = np.inf
        min_doc_idx = np.argsort(distance)[:100]

        for b in min_doc_idx:
            execution_string = 'INSERT INTO doc_doc (id, doc_a, doc_b, score) VALUES(NULL, ?, ?, ?)'
            cur.execute(execution_string, [str(a]), str(b), distance[b]])

    con.commit()

def write_doc_topic(con, cur, gamma_file):
    cur.execute('CREATE TABLE doc_topic (id INTEGER PRIMARY KEY, doc INTEGER, topic INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX doc_topic_idx1 ON doc_topic(doc)')
    cur.execute('CREATE INDEX doc_topic_idx2 ON doc_topic(topic)')
    con.commit()

    docs = np.loadtxt(gamma_file, 'r')
    # for each line in the gamma file
    for doc_no,doc in enumerate(docs):
        for i in range(len(doc)):
            ins = 'INSERT INTO doc_topic (id, doc, topic, score) '
            ins += 'VALUES(NULL, ?, ?, ?)'
            cur.execute(ins, [doc_no, i, doc[i]])

    con.commit()


def write_topics(con, cur, beta_file, vocab):
    """
    For each topic, write the first 3 most probably words to
    """
    cur.execute('CREATE TABLE topics (id INTEGER PRIMARY KEY, title VARCHAR(100))')
    con.commit()

    #NOTE: What is the following line for and why doesn't it raise an error?
    topics_file = open(filename, 'a')

    beta = np.loadtxt(beta_file)
    indices = np.argsort(beta, axis=1)
    for index in indices: # note this breaks ties differently than old code
        ins = 'INSERT INTO topics (id, title) VALUES(NULL, ?)'
        buf = "{%s, %s, %s}" % (vocab[index[0]],
                                vocab[index[1]],
                                vocab[index[2]])
        cur.execute(ins, [buffer(buf)])
    con.commit()


def write_topic_term(con, cur, beta_file):
    cur.execute('CREATE TABLE topic_term (id INTEGER PRIMARY KEY, topic INTEGER, term INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX topic_term_idx1 ON topic_term(topic)')
    cur.execute('CREATE INDEX topic_term_idx2 ON topic_term(term)')
    con.commit()

    topic_no = 0
    topic_term_file = open(filename, 'a')

    for topic in file(beta_file, 'r'):
        topic = map(float, topic.split())
        indices = range(len(topic)) # note: len(topic) should be the same as len(vocab)
        indices.sort(lambda x,y: -cmp(topic[x], topic[y]))
        for i in range(len(topic)):
            cur.execute('INSERT INTO topic_term (id, topic, term, score) VALUES(NULL, ?, ?, ?)', [topic_no, indices[i], topic[indices[i]]])
        topic_no = topic_no + 1

    con.commit()


def write_topic_topic(con, cur, beta_file):
    cur.execute('CREATE TABLE topic_topic (id INTEGER PRIMARY KEY, topic_a INTEGER, topic_b INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX topic_topic_idx1 ON topic_topic(topic_a)')
    cur.execute('CREATE INDEX topic_topic_idx2 ON topic_topic(topic_b)')
    con.commit()
    # for each line in the beta file
    read_file = file(beta_file, 'r')
    topics = []
    topic_no = 0
    for topic in read_file:
        topics.append(map(float, topic.split()))
        topic_no = topic_no +1

    topica_count = 0
    topic_by_topic = []
    for topica in topics:
        #topic_sim = r
        topicb_count = 0
        for topicb in topics:
            if topic_by_topic.count((topicb_count, topica_count)) != 0:
                topicb_count +=1
                continue
            score = get_topic_score(topica, topicb)
            cur.execute('INSERT INTO topic_topic (id, topic_a, topic_b, score) VALUES(NULL, ?, ?, ?)', [topica_count, topicb_count, score])

            topic_by_topic.append((topica_count, topicb_count))
            topicb_count = topicb_count + 1
        topica_count = topica_count + 1

    con.commit()



def write_term_term(con, cur, beta_file, no_vocab):
    v = {}

    cur.execute('CREATE TABLE term_term (id INTEGER PRIMARY KEY, term_a INTEGER, term_b INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX term_term_idx1 ON term_term(term_a)')
    cur.execute('CREATE INDEX term_term_idx2 ON term_term(term_b)')
    con.commit()

    for i in range(no_vocab):
	    v[i] = []

    for topic in file(beta_file, 'r'):
        topic = map(float, topic.split())
        for i in range(no_vocab):
            v[i].append(math.sqrt(math.exp(topic[i])))

    for terma in range(no_vocab):
        if terma % 1000 == 0:
            print "term " + str(terma)
        term_by_term = {}
        for termb in range(terma, len(vocab)):
            score = get_term_score(v[terma], v[termb])
            if score == 0:
                continue
            elif len(term_by_term) < 100:
                term_by_term[score] = (terma, termb)
            else:
                max_score = max(term_by_term.keys())
                if max_score > score:
                    del term_by_term[max_score]
                    term_by_term[score] = (terma, termb)

        for term in term_by_term:
            execution_string = 'INSERT INTO term_term (id, term_a, term_b, score) VALUES(NULL, ?, ?, ?)'
            cur.execute(execution_string, [term_by_term[term][0], term_by_term[term][1], term])

    con.commit()

def write_doc_term(con, cur, wordcount_file, no_words):
    cur.execute('CREATE TABLE doc_term (id INTEGER PRIMARY KEY, doc INTEGER, term INTEGER, score FLOAT)')
    cur.execute('CREATE INDEX doc_term_idx1 ON doc_term(doc)')
    cur.execute('CREATE INDEX doc_term_idx2 ON doc_term(term)')
    con.commit()

    doc_no = 0
    for doc in file(wordcount_file, 'r'):
        doc = doc.split()[1:]
        terms = {}
        for term in doc:
            terms[int(term.split(':')[0])] = int(term.split(':')[1])

        for i in range(no_words):
            score = 0
            if terms.has_key(i):
                score = terms[i]
                execution_string = 'INSERT INTO doc_term (id, doc, term, score) VALUES(NULL, ?, ?, ?)'
                cur.execute(execution_string, [doc_no, i, score])

        doc_no += 1

    con.commit()

def write_terms(con, cur, terms_file):
    cur.execute('CREATE TABLE terms (id INTEGER PRIMARY KEY, title VARCHAR(100))')
    con.commit()

    for line in open(terms_file, 'r'):
        cur.execute('INSERT INTO terms (id, title) VALUES(NULL, ?)', [buffer(line.strip())])

    con.commit()

def write_docs(con, cur, docs_file):
    cur.execute('CREATE TABLE docs (id INTEGER PRIMARY KEY, title VARCHAR(100))')
    con.commit()

    for line in open(docs_file, 'r'):
        cur.execute('INSERT INTO docs (id, title) VALUES(NULL, ?)', [buffer(line.strip())])

    con.commit()


### main ###

if (__name__ == '__main__'):
    if (len(sys.argv) != 7):
       print 'usage: python generate_csvs.py <db-filename> <doc-wordcount-file> <beta-file> <gamma-file> <vocab-file> <doc-file>\n'
       sys.exit(1)

    filename = sys.argv[1]
    doc_wordcount_file = sys.argv[2]
    beta_file = sys.argv[3]
    gamma_file = sys.argv[4]
    vocab_file = sys.argv[5]
    doc_file = sys.argv[6]

    # connect to database, which is presumed to not already exist
    con = sqlite3.connect(filename)
    cur = con.cursor()

    # pre-process vocab, since several of the below functions need it in this format
    vocab = file(vocab_file, 'r').readlines()
    vocab = map(lambda x: x.strip(), vocab)

    # write the relevant rlations to the database, see individual functions for details
    print "writing terms to db..."
    write_terms(con, cur, vocab_file)

    print "writing docs to db..."
    write_docs(con, cur, doc_file)

    print "writing doc_doc to db..."
    write_doc_doc(con, cur, gamma_file)

    print "writing doc_topic to db..."
    write_doc_topic(con, cur, gamma_file)

    print "writing topics to db..."
    write_topics(con, cur, beta_file, vocab)

    print "writing topic_term to db..."
    write_topic_term(con, cur, beta_file)

    print "writing topic_topic to db..."
    write_topic_topic(con, cur, beta_file)

    print "writing term_term to db..."
    write_term_term(con, cur, beta_file, len(vocab))

    print "writing doc_term to db..."
    write_doc_term(con, cur, doc_wordcount_file, len(vocab))

