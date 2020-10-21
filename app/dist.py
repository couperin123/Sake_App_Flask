import pandas as pd
import numpy as np
import sklearn
from sklearn.neighbors import NearestNeighbors

def sake_distance(db, sakeid):
    # print(query)
    df = pd.read_sql('sake', con=db.engine, index_col='index')
    # Use Amakara, Notan for the distance calculation
    nn_col = ['Amakara', 'Notan']
    features = df[nn_col].to_numpy()
    sakedfrow = df.index.get_loc(int(sakeid))
    # print(df.iloc[sakedfrow,:])
    nn = NearestNeighbors(n_neighbors=10, algorithm= 'brute', metric= 'cosine').fit(features)
    print(df.head())
    dists, indices = nn.kneighbors([features[sakedfrow]])
    # print(df.iloc[indices[0], 0:8])
    # print(df.loc[int(sakeid),:])
    # print(type(sakeid))
    # print("distance:", dists)
    # print("indices:", indices)
    return dists[0].tolist(), df.index[indices[0]].tolist();
