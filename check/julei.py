import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# 假设 data_list 是你的原始字符串列表
with open('check/fofa_result_ZTE-路由器.json', 'r', encoding='utf-8') as f:
    data_list = f.readlines()

# 1. 文本向量化（TF-IDF）
vectorizer = TfidfVectorizer(max_features=2000)
X = vectorizer.fit_transform(data_list)

# 2. 聚类
n_clusters = 2  # 可调整
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
labels = kmeans.fit_predict(X)

# 3. 降维可视化
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X.toarray())

plt.figure(figsize=(8, 6))
for i in range(n_clusters):
    plt.scatter(X_pca[labels == i, 0], X_pca[labels == i, 1], label=f'Cluster {i}')
plt.legend()
plt.xlabel('PCA1')
plt.ylabel('PCA2')
plt.title('Text Clustering Visualization')
plt.show()