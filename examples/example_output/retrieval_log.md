

---

## Query: How does the paper propose to calculate the coefficient α for the Weighted Cross Entropy Loss?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"Sample Weight Coefficient (α_i)","OBJECT","The weight coefficient $\alpha_i$ is associated with the i-th sample and modulates its contribution to the overall loss in weighted cross-entropy formulations. It is often calculated using the inverse frequency of the sample’s class (e.g., $\log(\frac{n - n_t}{n_t} + K)$, where $n_t$ is the count of class $t$, $n$ is the total number of samples, and $K$ is a tunable hyperparameter). This weighting scheme assigns higher importance to minority-class samples to counteract data imbalance.",3
1,"IMAGE_3","ORI_IMG",""The image displays a mathematical equation labeled as 'CE' (Cross-Entropy), which is commonly used in machine learning for classification tasks, particularly in the context of multi-class or binary classification with probabilistic outputs. The equation is written in LaTeX-style mathematical notation and reads: \[ \mathrm{CE} = -\frac{1}{N} \sum_{i} \alpha_i \sum_{j \in \{0,1\}} y_{ij} \log p_{ij} \]This formula represents a weighted cross-entropy loss function. Here, \( N \) denotes the total number of samples in the dataset. The outer summation is over individual samples \( i \), and each sample contributes to the loss scaled by a weight factor \( \alpha_i \), where \( \alpha_i \in [0,1] \). This weighting allows for adjusting the importance of different samples, typically to address class imbalance. The inner summation is over the possible class labels \( j \in \{0,1\} \), indicating a binary classification setting. For each sample \( i \) and class \( j \), \( y_{ij} \) is the true label (usually 0 or 1 in one-hot encoding), and \( p_{ij} \) is the predicted probability assigned by the model to class \( j \) for sample \( i \). The logarithmic term \( \log p_{ij} \) penalizes low-confidence correct predictions more heavily. The negative sign ensures that minimizing the CE loss corresponds to maximizing the likelihood of correct predictions. The context provided explains that this formulation allows for unequal treatment of samples via \( \alpha_i \), which can be set based on inverse class frequency or tuned via hyperparameters such as \( K \) in the expression \( \log \left( \frac{n - n_t}{n_t} + K \right) \), where \( n_t \) is the count of samples in class \( t \) and \( n \) is the total number of training samples. This adjustment reduces the influence of majority classes and increases that of minority classes, helping mitigate bias in imbalanced datasets."",9
2,Cross Entropy Loss,IMG_ENTITY,"The cross-entropy (CE) loss function used in binary classification tasks, as represented by the mathematical formula CE = -1/N ∑∑ y_ij log p_ij. This formula computes the average cross-entropy loss over N training instances, where y_ij is the true label and p_ij is the predicted probability for class j ∈ {0,1}. The image corresponds to the formal definition of this loss function, which is discussed in the text as a standard training objective in data-imbalanced NLP tasks.",2
3,"Weighted Cross-Entropy Loss (WCE)","ORGANIZATION","Weighted Cross-Entropy Loss (WCE) extends the standard Cross-Entropy Loss by introducing a sample-specific or class-specific weighting factor α_i to adjust the contribution of each instance during training. This is particularly useful in imbalanced datasets, where minority classes are assigned higher weights—often computed using inverse class frequency or formulas like log((n − n_t)/n_t + K), where n_t is the count of class t and n is the total number of samples. While effective, improper weighting can bias the model toward rare classes.",4
4,"IMAGE_2","ORI_IMG",""The image displays a mathematical formula representing the cross-entropy (CE) loss function used in binary classification tasks. The formula is written in LaTeX-style notation and reads: CE = -\frac{1}{N} \sum_{i} \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}. This equation computes the average cross-entropy loss over N training instances. For each instance i, the sum is taken over the two possible class labels j ∈ {0,1}, where y_ij represents the true label (either 0 or 1) and p_ij denotes the predicted probability for class j. The logarithm of the predicted probability is weighted by the true label, ensuring that only the log-probability of the correct class contributes to the loss. The negative sign ensures the loss is positive, and dividing by N normalizes the total loss across all samples. The context explains that this formulation applies to binary classification with one-hot encoded labels and can be extended to multi-class settings. It also mentions that each training instance contributes equally to the final objective, and strategies like class weighting or resampling are used when unequal treatment of instances is desired."",10
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"Cross-Entropy Loss (CE)","IMAGE_2","CE是从image_2中提取的实体。",10.0,26
1,"Cross-Entropy Loss (CE)","IMAGE_3","CE是从image_3中提取的实体。",10.0,25
2,"Cross-Entropy Loss (CE)","Weighted Cross-Entropy Loss (WCE)",""WCE builds upon CE by introducing a weight α_i to adjust the influence of individual samples, making it suitable for imbalanced datasets."",7.0,20
3,"Cross-Entropy Loss (CE)","Sample Weight Coefficient (α_i)","Each sample's contribution to the cross-entropy is weighted by α_i.",8.0,19
4,"IMAGE_2","Total Number of Samples (N)","N是从image_2中提取的实体。",10.0,14
5,"IMAGE_2","Summation Over Classes (∑_j)","Summation over j是从image_2中提取的实体。",10.0,13
6,"IMAGE_3","Predicted Class Probability (p_ij)","p_ij是从image_3中提取的实体。",10.0,13
7,"IMAGE_3","True Label Indicator (y_ij)","y_ij是从image_3中提取的实体。",10.0,13
8,"IMAGE_2","Summation Over Samples (∑_i)","Summation over i是从image_2中提取的实体。",10.0,13
9,"IMAGE_3","Total Number of Samples (N)","N是从image_3中提取的实体。",10.0,13
10,"IMAGE_2","True Label (y_ij)","y_ij是从image_2中提取的实体。",10.0,13
11,"IMAGE_7","Weighted Cross-Entropy Loss (WCE)","WCE是从image_7中提取的实体。",10.0,13
12,"IMAGE_2","Predicted Probability (p_ij)","p_ij是从image_2中提取的实体。",10.0,13
13,"Class Label Index (j)","IMAGE_2","j是从image_2中提取的实体。",10.0,12
14,"IMAGE_2","Natural Logarithm (log)","log是从image_2中提取的实体。",10.0,12
15,"IMAGE_3","Natural Logarithm Function (log)","log是从image_3中提取的实体。",10.0,12
16,"IMAGE_2",Cross Entropy Loss,"IMAGE_2" is the image of Cross Entropy Loss.,10.0,12
17,"IMAGE_3","Sample Weight Coefficient (α_i)","α_i是从image_3中提取的实体。",10.0,12
18,""Binary Class Index Set (j ∈ {0,1})"","IMAGE_3",""j∈{0,1}是从image_3中提取的实体。"",10.0,11
19,"IMAGE_3","Summation Operator (Σ)","Σ是从image_3中提取的实体。",10.0,11
20,"IMAGE_2","Sample Index (i)","i是从image_2中提取的实体。",10.0,11
21,"IMAGE_3",Cross Entropy Loss,"IMAGE_3" is the image of Cross Entropy Loss.,10.0,11
22,"Loss Function Formula (One Sample x_i)","Weighted Cross-Entropy Loss (WCE)",""The WCE formula incorporates α_i into the CE framework, fitting within the overall formula structure for one sample."",8.0,11
23,"Loss Functions in Machine Learning","Weighted Cross-Entropy Loss (WCE)",""WCE is a variant of the loss function family, specifically a weighted version of cross-entropy."",8.0,11
24,"Sample Weight Coefficient (α_i)","True Label Indicator (y_ij)","The weight α_i scales the contribution of the true label y_ij for each sample.",6.0,7
    ```
    -----Sources-----
    ```csv
    id,content
    ```
    

### Initial LLM Response

The paper proposes to calculate the sample weight coefficient **αᵢ** in the Weighted Cross-Entropy (WCE) Loss using a formulation based on **inverse class frequency**, specifically:

$$
\alpha_i = \log\left( \frac{n - n_t}{n_t} + K \right)
$$

Where:
- $ n $ is the total number of samples in the dataset,
- $ n_t $ is the number of samples belonging to the class $ t $ of the i-th sample,
- $ K $ is a tunable hyperparameter that stabilizes the logarithm and prevents extreme weights when $ n_t $ is very small.

This approach assigns **higher weights to samples from minority classes** (i.e., classes with smaller $ n_t $), thereby increasing their contribution to the total loss and helping to mitigate bias caused by class imbalance during training.

This definition of $ \alpha_i $ is explicitly described in the entity **"Sample Weight Coefficient (α_i)"**, which is directly linked to both the **Weighted Cross-Entropy Loss (WCE)** and the mathematical expression shown in **IMAGE_3**. The use of the logarithmic transformation softens the effect of extreme inverse frequencies while still emphasizing rare classes.

### Multimodal Processing (2 images)

**Image**: examples/example_working/images/image_2.jpg
**Response**: ### **Table Analysis**

The provided data includes an entity named **"Sample Weight Coefficient (α_i)"** with the following description:

> *"The weight coefficient $\alpha_i$ is associated with the i-th sample and modulates its contribution to the overall loss in weighted cross-entropy formulations. It is often calculated using the inverse frequency of the sample’s class (e.g., $\log(\frac{n - n_t}{n_t} + K)$, where $n_t$ is the count of class $t$, $n$ is the total number of samples, and $K$ is a tunable hyperparameter). This weighting scheme assigns higher importance to minority-class samples to counteract data imbalance."*

This directly specifies how α_i is computed:
- It uses **inverse class frequency**, specifically:  
  $$
  \alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
  $$
  where:
  - $n_t$: number of samples in class $t$,
  - $n$: total number of samples,
  - $K$: a tunable hyperparameter (likely added for numerical stability or to control the magnitude of weights).

Additionally, the relationship between **Weighted Cross-Entropy Loss (WCE)** and **Sample Weight Coefficient (α_i)** confirms that α_i scales the contribution of each sample in the loss function.

---

### **Image Analysis**

Two images are referenced:
- **IMAGE_2**: Displays the standard Cross-Entropy (CE) loss formula:
  $$
  \mathrm{CE} = -\frac{1}{N} \sum_{i} \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}
  $$
  This does not include any weighting term (no α_i), so it represents the baseline unweighted CE.

- **IMAGE_3**: Shows the **Weighted Cross-Entropy Loss** formula:
  $$
  \mathrm{CE} = -\frac{1}{N} \sum_{i} \alpha_i \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}
  $$
  Here, the **weight coefficient α_i** is explicitly included as a multiplicative factor outside the inner summation over classes. This confirms that each sample's contribution to the loss is scaled by α_i.

From IMAGE_3, we can extract:
- The presence of **α_i** in the formula.
- The structure of the weighted version: the outer sum over samples $i$ now includes α_i.
- No explicit calculation of α_i is shown in the image itself, but the context from the table links this to the inverse frequency formula.

---

### **Integrated Insights**

The paper proposes to calculate the coefficient **α_i** using a **class-based weighting scheme** derived from **inverse class frequency**, specifically:

$$
\alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
$$

where:
- $n_t$ is the count of samples belonging to the class $t$ of sample $i$,
- $n$ is the total number of training samples,
- $K$ is a tunable hyperparameter to prevent division-by-zero or extreme values.

This formulation ensures:
- **Higher weights** are assigned to samples from **minority classes** (since $n_t$ is small → $\frac{n - n_t}{n_t}$ is large → log value is large),
- **Lower weights** are assigned to samples from **majority classes**,
- Thus, the model is encouraged to pay more attention to underrepresented classes during training.

This approach is implemented in the **Weighted Cross-Entropy Loss (WCE)**, which modifies the standard CE loss by multiplying each sample’s contribution by α_i, as seen in IMAGE_3.

---

### **Conclusion**

The paper proposes calculating the coefficient α_i for the Weighted Cross-Entropy Loss using the formula:

$$
\alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
$$

This method adjusts the loss based on class frequency, giving greater importance to minority-class samples to mitigate the effects of class imbalance. The visual evidence from IMAGE_3 confirms the inclusion of α_i in the loss function, while the textual description provides the exact computation rule.

**Image**: examples/example_working/images/image_3.jpg
**Response**: ### Table Analysis

The entity **"Sample Weight Coefficient (α_i)"** is described in the table as follows:

> "The weight coefficient $\alpha_i$ is associated with the i-th sample and modulates its contribution to the overall loss in weighted cross-entropy formulations. It is often calculated using the inverse frequency of the sample’s class (e.g., $\log(\frac{n - n_t}{n_t} + K)$, where $n_t$ is the count of class $t$, $n$ is the total number of samples, and $K$ is a tunable hyperparameter). This weighting scheme assigns higher importance to minority-class samples to counteract data imbalance."

This indicates that the coefficient $\alpha_i$ is computed based on the **inverse class frequency**, specifically using the formula:
$$
\alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
$$
where:
- $n_t$: number of samples in class $t$,
- $n$: total number of samples,
- $K$: a tunable hyperparameter.

This formulation ensures that **minority classes receive higher weights**, thereby mitigating bias caused by class imbalance.

---

### Image Analysis

The image labeled **IMAGE_3** contains the following mathematical expression:
$$
\mathrm{CE} = -\frac{1}{N} \sum_{i} \alpha_i \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}
$$
This confirms the presence of the **weighting factor $\alpha_i$** in the cross-entropy loss function. The description of IMAGE_3 further clarifies:
> "The context provided explains that this formulation allows for unequal treatment of samples via $\alpha_i$, which can be set based on inverse class frequency or tuned via hyperparameters such as $K$ in the expression $\log \left( \frac{n - n_t}{n_t} + K \right)$..."

Thus, the image reinforces the idea that $\alpha_i$ is derived from **inverse class frequency**, with an added hyperparameter $K$ for tuning.

---

### Integrated Insights

Combining information from both the **table** and **image**, we conclude:

- The paper proposes calculating the coefficient $\alpha_i$ using:
  $$
  \alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
  $$
  where $n_t$ is the count of samples in class $t$, $n$ is the total number of samples, and $K$ is a tunable hyperparameter.
- This approach emphasizes **minority-class samples** by assigning them higher weights, thus addressing **class imbalance**.
- The use of $K$ allows for **fine-tuning** the weight scaling, preventing overfitting to rare classes.
- The inclusion of $\alpha_i$ in the loss function (as shown in IMAGE_3) modifies the standard cross-entropy loss into a **weighted version**, enabling more balanced training across classes.

This method is consistent with common practices in handling imbalanced datasets in machine learning, particularly in NLP and classification tasks.

### Merged Multimodal Response

The paper proposes to calculate the coefficient αᵢ for the Weighted Cross-Entropy Loss using a class-based inverse frequency weighting scheme. Specifically, the formula is:

\[
\alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
\]

where:  
- \(n_t\) is the number of samples in class \(t\) (the class of the i-th sample),  
- \(n\) is the total number of training samples,  
- \(K\) is a tunable hyperparameter added for numerical stability and to control the magnitude of the weights.

This formulation assigns higher weights to samples from minority classes (where \(n_t\) is small), thereby increasing their contribution to the loss and helping to mitigate class imbalance during training. The use of this αᵢ is explicitly incorporated into the loss function as shown in the weighted cross-entropy expression:

\[
\mathrm{WCE} = -\frac{1}{N} \sum_{i} \alpha_i \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}
\]

Thus, the paper combines inverse class frequency with a logarithmic transformation and a tunable offset \(K\) to compute sample-specific weights that promote balanced learning across imbalanced classes.

### Final Response

The paper proposes to calculate the coefficient αᵢ for the Weighted Cross-Entropy Loss using a **class-based inverse frequency weighting scheme** with a logarithmic transformation. Specifically, the formula is:

\[
\alpha_i = \log\left(\frac{n - n_t}{n_t} + K\right)
\]

where:  
- \(n_t\) is the number of samples in class \(t\) (the class of the i-th sample),  
- \(n\) is the total number of training samples,  
- \(K\) is a tunable hyperparameter added for numerical stability and to control the magnitude of the weights.

This formulation assigns **higher weights to samples from minority classes** (where \(n_t\) is small), thereby increasing their contribution to the loss and helping to mitigate class imbalance during training. The coefficient αᵢ is incorporated into the weighted cross-entropy loss as:

\[
\mathrm{WCE} = -\frac{1}{N} \sum_{i} \alpha_i \sum_{j \in \{0,1\}} y_{ij} \log p_{ij}
\]

The use of the logarithm softens extreme weight values while still emphasizing rare classes, and the hyperparameter \(K\) prevents division-by-zero or excessively large weights when \(n_t\) is very small.

---

## Query: Is the OntoNotes4.0 dataset used for the Named Entity Recognition task Chinese or English?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"CHINESE ONTONOTES4.0 NER DATASET",GEO,"Chinese OntoNotes4.0 is a named entity recognition dataset focused on Chinese language data, used in experiments evaluating the Tversky Index hyperparameters. In the image table, it appears as 'CHINESE ONTO4.0', showing scores that peak at 84.67 when α = 0.6.",4
1,"ONTONOTES4.0","GEO",""Chinese OntoNotes4.0 is a named entity recognition dataset consisting of news-domain texts with 18 entity types, used with a data split following Wu et al. (2019)."<SEP>"OntoNotes4.0 is an earlier version of the OntoNotes NER benchmark dataset, used for evaluating entity recognition across diverse text genres."<SEP>"OntoNotes4.0 is another NER dataset included in the evaluation, showing strong performance with the proposed approach."",3
2,"WU ET AL.","PERSON","Wu et al. are researchers whose data split methodology for Chinese OntoNotes4.0 was adopted in this work.",1
3,"CHINESE ONTONOTES4.0","UNKNOWN","The data split for Chinese OntoNotes4.0 follows the approach used by Wu et al. (2019).",1
4,"CHINESE ONTONOTES 4.0",GEO,"The Chinese-language portion of the OntoNotes 4.0 corpus, geographically and linguistically tied to Chinese-speaking regions. It is the Chinese version of the OntoNotes corpus, used for evaluating syntactic and semantic parsing models on Chinese text.",9
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,""BERT (DEVLIN ET AL., 2018)"","CHINESE ONTONOTES 4.0","BERT-Tagger achieves an F1 of 79.16 on Chinese OntoNotes 4.0.",7.0,41
1,"CHINESE ONTONOTES 4.0","IMAGE_18","Chinese OntoNotes 4.0是从image_18中提取的实体。",10.0,26
2,"CHINESE ONTONOTES 4.0",""LATTICE-LSTM (ZHANG AND YANG, 2018)"","Lattice-LSTM is applied to the Chinese portion of OntoNotes 4.0.",9.0,19
3,""BERT-MRC (LI ET AL., 2019)"","CHINESE ONTONOTES 4.0","BERT-MRC achieves an F1 of 82.11 on Chinese OntoNotes 4.0.",8.0,19
4,"ARXIV:1805.02023","ONTONOTES4.0","The arXiv paper uses Chinese OntoNotes4.0 for named entity recognition experiments.",8.0,15
5,"DICE LOSS FOR DATA-IMBALANCED NLP TASKS","ONTONOTES4.0","The proposed method achieves competitive or better results on the OntoNotes4.0 NER task.",8.0,15
6,"BERT-MRC+DSC","CHINESE ONTONOTES 4.0","BERT-MRC+DSC achieves the highest F1 of 84.47 on Chinese OntoNotes 4.0.",9.0,14
7,"BERT-MRC+FL","CHINESE ONTONOTES 4.0","BERT-MRC+FL improves to an F1 of 83.30 on Chinese OntoNotes 4.0.",8.0,14
8,"BERT-MRC+DL","CHINESE ONTONOTES 4.0","BERT-MRC+DL achieves an F1 of 84.01 on Chinese OntoNotes 4.0.",8.0,14
9,"CHINESE ONTONOTES 4.0",""GLYCE-BERT (WU ET AL., 2019)"","Glyce-BERT achieves an F1 of 80.62 on Chinese OntoNotes 4.0.",8.0,13
10,"CHINESE ONTONOTES 4.0","ONTONOTES 4.0","Chinese OntoNotes 4.0 is the Chinese subset of the OntoNotes 4.0 corpus.",10.0,11
11,"ONTONOTES4.0","TABLE 5","Table 5 shows results for NER models tested on the OntoNotes4.0 dataset.",9.0,10
12,"CHINESE ONTONOTES4.0 NER DATASET","TABLE 10",""Table 10 contains experimental results specifically derived from the Chinese OntoNotes4.0 NER dataset, showing F1 scores at varying α values."",9.0,10
13,"CHINESE ONTONOTES4.0 NER DATASET","α (alpha)",""The value of α influences the performance score on the Chinese Onto4.0 benchmark, with the highest score (84.67) achieved at α = 0.6."",8.0,10
14,"CHINESE ONTONOTES4.0 NER DATASET","IMAGE_23","Chinese Onto4.0是从image_23中提取的实体。",10.0,9
15,"CHINESE ONTONOTES4.0 NER DATASET","ENGLISH QUOREF MRC DATASET",""Both benchmarks are compared side by side in the table, allowing for direct comparison of performance across languages and α values."",7.0,8
16,"CHINESE ONTONOTES4.0","WU ET AL.","The data split for Chinese OntoNotes4.0 follows the approach used by Wu et al. (2019).",8.0,2
    ```
    -----Sources-----
    ```csv
    id,content
0,"</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling the tradeoff between false-negatives and false-positives. In this subsection, we explore the effect of hyperparameters (i.e., $\alpha$ and $\beta$ ) in TI to test how they manipulate the tradeoff. We conduct experiments on the Chinese OntoNotes4.0 NER dataset and English QuoRef MRC dataset. Experimental results are shown in Table 10. The highest F1 on Chinese OntoNotes4.0 is 84.67 when $\alpha$ is set to 0.6 while for QuoRef, the highest F1 is 68.44 when $\alpha$ is set to 0.4. In addition, we can observe that the performance varies a lot as $\alpha$ changes in distinct datasets, which shows that the hyperparameters $\alpha , \beta$ acturally play an important role in TI.

# 6 Conclusion

In this paper, we propose the dice-based loss to narrow down the gap between training objective and evaluation metrics (F1 score). Experimental results show that the proposed loss function help

<table><tr><td>α</td><td>Chinese Onto4.0</td><td>English QuoRef</td></tr><tr><td>α=0.1</td><td>80.13</td><td>63.23</td></tr><tr><td>α=0.2</td><td>81.17</td><td>63.45</td></tr><tr><td>α= 0.3</td><td>84.22</td><td>65.88</td></tr><tr><td>α=0.4</td><td>84.52</td><td>68.44</td></tr><tr><td>α=0.5</td><td>84.47</td><td>67.52</td></tr><tr><td>α=0.6</td><td>84.67</td><td>66.35</td></tr><tr><td>α=0.7</td><td>81.81</td><td>65.09</td></tr><tr><td>α=0.8</td><td>80.97</td><td>64.13</td></tr><tr><td>α= 0.9</td><td>80.21</td><td>64.84</td></tr></table>

Table 10: The effect of hyperparameters in Tversky Index. We set $\beta = 1 - \alpha$ and thus we only list $\alpha$ here.

to achieve significant performance boost without changing model architectures.

# Acknowledgement

We thank all anonymous reviewers, as well as Qinghong Han, Wei Wu and Jiawei Wu for their comments and suggestions. The work is supported by the National Natural Science Foundation of China (NSFC No. 61625107 and 61751209).

# References

Bernd Bohnet, Ryan T. McDonald, Gonc¸alo Simoes, ˜ Daniel Andor, Emily Pitler, and Joshua Maynez. 2018. Morphosyntactic tagging with a meta-bilstm model over context sensitive token encodings. In Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics, ACL 2018, Melbourne, Australia, July 15-20, 2018, Volume 1: Long Papers, pages 2642–2652.

Haw-Shiuan Chang, Erik G. Learned-Miller, and Andrew McCallum. 2017. Active bias: Training more accurate neural networks by emphasizing high variance samples. In NIPS.

N. V. Chawla, K. W. Bowyer, Lawrence O. Hall, and W. P. Kegelmeyer. 2002. Smote: Synthetic minority over-sampling technique. J. Artif. Intell. Res., 16:321– 357.

Danqi Chen, Adam Fisch, Jason Weston, and Antoine Bordes. 2017. Reading wikipedia to answer opendomain questions. arXiv preprint arXiv:1704.00051.

Kean Chen, Jianguo Li, Weiyao Lin, John See, Ji Wang, Lingyu Duan, Zhibo Chen, Changwei He, and Junni Zou. 2019. Towards accurate one-stage object detection with ap-loss. In IEEE Conference on Computer Vision and Pattern Recognition, CVPR 2019, Long Beach, CA, USA, June 16-20, 2019, pages 5119–5127.

Shijuan Chen, Haibo He, and Edwardo A. Garcia. 2010. Ramoboost: Ranked minority oversampling in boosting. IEEE Transactions on Neural Networks, 21:1624– 1642.

Kevin Clark, Minh-Thang Luong, Christopher D. Manning, and Quoc V. Le. 2018. Semi-supervised sequence modeling with cross-view training. In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Procfessing, Brussels, Belgium, October 31 - November 4, 2018, pages 191"
1,"and F1.

Baselines We use the following baselines:

• ELMo: a tagging model with pretraining from Peters et al. (2018).   
• Lattice-LSTM: Zhang and Yang (2018) constructs a word-character lattice, only used in Chinese datasets.   
CVT: Clark et al. (2018) uses Cross-View Training(CVT) to improve the representations of a Bi-LSTM encoder.   
• Bert-Tagger: Devlin et al. (2018) treats NER as a tagging task.   
• Glyce-BERT: Wu et al. (2019) combines Chinese glyph information with BERT pretraining.   
• BERT-MRC: Li et al. (2019) formulates NER as a machine reading comprehension task and achieves SOTA results on Chinese and English NER benchmarks.

Results Table 5 shows experimental results on NER datasets. DSC outperforms BERT-MRC(Li et al., 2019) by $+ 0 . 2 9$ , $+ 0 . 9 6$ , $+ 0 . 9 7$ and $+ 2 . 3 6$ respectively on CoNLL2003, OntoNotes5.0, MSRA and OntoNotes4.0. As far as we are concerned, we are setting new SOTA performances on all of the four NER datasets.

# 4.3 Machine Reading Comprehension

Settings The task of machine reading comprehension (MRC) (Seo et al., 2016; Wang et al., 2016; Wang and Jiang, 2016; Wang et al., 2016; Shen et al., 2017; Chen et al., 2017) predicts the answer span in the passage given a question and the passage. We followed the standard protocols in Seo et al. (2016), in which the start and end indexes of answer are predicted. We report Extract Match (EM) as well as F1 score on validation set. We use three datasets on this task: SQuAD v1.1, SQuAD v2.0 (Rajpurkar et al., 2016, 2018) and Quoref (Dasigi et al., 2019).

Baselines We used the following baselines:

• QANet: Yu et al. (2018b) builds a model based on convolutions and self-attentions. Convolutions are used to model local interactions and self-attention are used to model global interactions. BERT: Devlin et al. (2018) scores each candidate span and the maximum scoring span is used as a prediction.   
• XLNet: Yang et al. (2019) proposes a generalized autoregressive pretraining method that

Table 6: Experimental results for MRC task.   

<table><tr><td></td><td colspan="2">SQuAD v1.1</td><td colspan="2"> SQuAD v2.0</td><td colspan="2">QuoRef</td></tr><tr><td>Model</td><td>EM</td><td>F1</td><td>EM</td><td>F1</td><td>EM</td><td>F1</td></tr><tr><td>QANet (Yu et al., 2018b) BERT (Devlin et al., 2018)</td><td>73.6 84.1</td><td>82.7 90.9</td><td>- 78.7</td><td>1 81.9</td><td>34.41 58.44</td><td>38.26 64.95</td></tr><tr><td>BERT+FL</td><td>84.67 (+0.57)</td><td>91.25 (+0.35)</td><td>78.92 (+0.22)</td><td>82.20 (+0.30)</td><td>60.78 (+2.34)</td><td>66.19 (+1.24)</td></tr><tr><td>BERT+DL</td><td>84.83 (+0.73)</td><td>91.86 (+0.96)</td><td>78.99 (+0.29)</td><td>82.88 (+0.98)</td><td>62.03 (+3.59)</td><td>66.88 (+1.93)</td></tr><tr><td>BERT+DSC</td><td>85.34 (+1.24)</td><td>91.97 (+1.07)</td><td>79.02 (+0.32)</td><td>82.95 (+1.05)</td><td>62.44 (+4.00)</td><td>67.52 (+2.57)</td></tr><tr><td>XLNet (Yang et al., 2019)</td><td>88.95</td><td>94.52</td><td>86.12</td><td>88.79</td><td>64.52</td><td>71.49</td></tr><tr><td>XLNet+FL</td><td>88.90 (-0.05)</td><td>94.55 (+0.03)</td><td>87.04 (+0.92)</td><td>89.32 (+0.53)</td><td>65.19 (+0.67)</td><td>72.34 (+0.85)</td></tr><tr"
2,"2018. Chinese ner using lattice lstm. arXiv preprint arXiv:1805.02023.

# A Dataset Details

# A.1 Part-of-Speech Tagging

Datasets We conduct experiments on three widely used benchmark, i.e., Chinese Treebank $5 . 0 ^ { 2 } / 6 . 0 ^ { 3 }$ and $\mathrm { U D } 1 . 4 ^ { 4 }$ .

• CTB5 is a Chinese dataset for tagging and parsing, which contains 507,222 words, 824,983 characters and 18,782 sentences extracted from newswire sources, including 698 articles from Xinhua (1994-1998), 55 articles from Information Services Department of HKSAR (1997) and 132 articles from Sinorama Magazine (1996-1998 & 2000-2001).

• CTB6 is an extension of CTB5, containing 781,351 words, 1,285,149 characters and 28,295 sentences.

• UD is the abbreviation of Universal Dependencies, which is a framework for consistent annotation of grammar (parts of speech, morphological features, and syntactic dependencies) across different human languages. In this work, we use UD1.4 for Chinese POS tagging.

# A.2 Named Entity Recognition

Datasets For the NER task, we consider both Chinese datasets, i.e., OntoNotes $4 . 0 ^ { 5 }$ and MSRA6 , and English datasets, i.e., CoNLL2003 7 and OntoNote $5 . 0 ^ { 8 }$ .

• CoNLL2003 is an English dataset with 4 entity types: Location, Organization, Person and Miscellaneous. We followed data processing protocols in (Ma and Hovy, 2016).

• English OntoNotes5.0 consists of texts from a wide variety of sources and contains 18 entity types. We use the standard train/dev/test split of CoNLL2012 shared task.

• Chinese MSRA performs as a Chinese benchmark dataset containing 3 entity types. Data in MSRA is collected from news domain. Since the development set is not provided in the original MSRA dataset, we randomly split the training set into training and development splits by 9:1. We use the official test set for evaluation.

• Chinese OntoNotes4.0 is a Chinese dataset and consists of texts from news domain, which has 18 entity types. In this paper, we take the same data split as Wu et al. (2019) did.

# A.3 Machine Reading Comprephension

Datasets For MRC task, we use three datasets: $\mathrm { S Q u A D v 1 . 1 / v 2 . 0 ^ { 9 } }$ and Queref10 datasets.

• SQuAD v1.1 and SQuAD $\mathbf { v } 2 . \mathbf { 0 }$ are the most widely used QA benchmarks. SQuAD1.1 is a collection of 100K crowdsourced question-answer pairs, and SQuAD2.0 extends SQuAD1.1 allowing no short answer exists in the provided passage.

• Quoref is a QA dataset which tests the coreferential reasoning capability of reading comprehension systems, containing 24K questions over 4.7K paragraphs from Wikipedia.

# A.4 Paraphrase Identification

Datasets Experiments are conducted on two PI datasets: $\mathbf { M R P C } ^ { 1 1 }$ and $\mathrm { Q Q P ^ { 1 2 } }$ .

• MRPC is a corpus of sentence pairs automatically extracted from online news sources, with human annotations of whether the sentence pairs are semantically equivalent. The MRPC dataset has imbalanced classes (6800 pairs in total, and $68 \%$ for positive, $32 \%$ for negative).

QQP is a collection of question pairs from the community question-answering website Quora. The class distribution in QQP is also unbalanced (over 400,000 question pairs in total, and $37 \%$ for positive, $63 \%$ for negative)."
    ```
    

### Initial LLM Response

The **OntoNotes4.0 dataset** itself is **not exclusively Chinese or English**—it is a **multilingual corpus** that includes data in multiple languages, including **both English and Chinese**. However, in the context of the provided data:

- The entry **"CHINESE ONTONOTES4.0"** (and its variants like "CHINESE ONTONOTES4.0 NER DATASET") explicitly refers to the **Chinese-language portion** of the OntoNotes 4.0 corpus.
- This Chinese subset is used specifically for **Named Entity Recognition (NER)** tasks in several experiments cited, such as those involving BERT-MRC, Lattice-LSTM, and Tversky Index hyperparameter tuning.
- The description clarifies: *"Chinese OntoNotes4.0 is a named entity recognition dataset consisting of news-domain texts with 18 entity types"* and that it is the **Chinese version** of the OntoNotes corpus.

Meanwhile:
- There is also an **English OntoNotes5.0** mentioned in the sources (used alongside CoNLL2003), but **OntoNotes4.0 in this context predominantly refers to the Chinese variant** when discussed in relation to NER experiments in the provided tables and text.

### Conclusion:
In the specific context of the provided data and experiments, **OntoNotes4.0 is used as a Chinese Named Entity Recognition dataset**. The broader OntoNotes 4.0 corpus includes multiple languages, but the referenced usage here is **Chinese**.

---

## Query: Which model variant has the highest improvement in F1 score for the QuoRef dataset when compared to the base XLNet model?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"SCORE (F1-score)","OBJECT","Numerical performance metrics representing F1-scores across different experimental conditions and datasets. Higher SCORE values indicate better model performance in tasks such as question answering (QQP), named entity recognition (Chinese OntoNotes4.0), and machine reading comprehension (English QuoRef). The scores are reported in tables comparing baseline models (e.g., BERT) with variants using different loss functions (e.g., Dice Loss, DSC) and data augmentation strategies (+positive, +negative, etc.). For instance, in Table 8, BERT+DSC achieves the highest F1-score of 93.63 under the '+ positive & negative' augmentation setting, while in Table 10, the highest scores are 84.67 (Chinese Onto4.0) and 68.44 (English QuoRef) at specific α values.",2
1,"IMAGE_21","ORI_IMG","IMAGE_21 is a table titled "Table 8: The effect of different data augmentation ways for QQP in terms of F1-score," which presents a comparative analysis of F1-scores across four model configurations—BERT, BERT+FL, BERT+DL, and BERT+DSC—under five distinct data augmentation strategies: 'original', '+ positive', '+ negative', '- negative', and '+ positive & negative'. The table demonstrates how each augmentation approach affects model performance on the Quora Question Pairs (QQP) dataset.

For the base BERT model, the original F1-score is 91.3. Adding only positive examples (+ positive) improves performance to 92.27, while adding only negative examples (+ negative) reduces it to 90.08. Removing negative examples (- negative), which results in a balanced 50-50 class distribution by down-sampling negatives, further decreases performance to 89.73. In contrast, combining both positive and negative augmentations (+ positive & negative) yields the highest score of 93.14.

Similar trends are observed across the enhanced models. BERT+FL achieves an original score of 91.86 (+0.56 over BERT), with its best result (93.45, +0.31 over its own baseline) under the '+ positive & negative' condition. BERT+DL starts at 91.92 (+0.62) and peaks at 93.52 (+0.38) with combined augmentation. BERT+DSC shows the highest baseline at 92.11 (+0.81) and reaches 93.63 (+0.49) with '+ positive & negative'.

Across all models, the '+ positive & negative' strategy consistently delivers the highest F1-scores, with improvements ranging from +0.31 to +0.49 relative to each model’s original performance. Conversely, '+ negative' generally degrades performance—attributed to creating a highly imbalanced dataset (21% positive, 79% negative)—and '- negative', despite balancing the class distribution, also underperforms compared to the original setup, particularly for the base BERT model. The table thus highlights that strategic combination of both positive and negative data augmentation yields optimal results, whereas isolated or removal-based strategies tend to be",10
2,"XLNet+DSC","ORGANIZATION","XLNet+DSC applies Discriminative Self-Consistency (DSC) to the XLNet framework, achieving the best results among all XLNet variants. It obtains 89.78 F1 on MRPC (+0.58), 92.60 F1 on QQP (+0.79), 95.77 F1 on SQuAD v1.1 (+1.25), and 72.90 F1 on QuoRef (+1.41). These results highlight DSC’s ability to significantly boost performance even on top of strong pre-trained models like XLNet.",1
3,"F1","OBJECT","F1 score is the harmonic mean of precision and recall, providing a single balanced metric to evaluate model performance in tasks such as Named Entity Recognition and Part-of-Speech tagging. It is especially useful when dealing with imbalanced datasets, as it accounts for both false positives and false negatives. In the experimental results, F1 scores are used as the primary indicator of model effectiveness, with improvements from variants like BERT-MRC+DSC reported as absolute gains (e.g., '+2.36') over baseline models.",1
4,"F1 SCORE",CONCEPT,"F1 Score, the harmonic mean of precision and recall, used to evaluate the performance of classification models. It is an F1-oriented statistic used to measure the similarity between two sets, commonly applied in evaluating model predictions against ground truth in machine learning contexts.",2
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"DICE SIMILARITY COEFFICIENT (DSC)","F1 SCORE",""The Dice Similarity Coefficient (DSC) is equal to the F1 score, both representing the harmonic mean of precision and recall."",10.0,41
1,"BERT+DSC","IMAGE_21","BERT+DSC是从image_21中提取的实体。",10.0,30
2,"BERT+DL","IMAGE_21","BERT+DL是从image_21中提取的实体。",10.0,30
3,"BERT+FL","IMAGE_21","BERT+FL是从image_21中提取的实体。",10.0,27
4,"BERT+CE","IMAGE_21","BERT是从image_21中提取的实体。",10.0,19
5,"F1","IMAGE_18","F1是从image_18中提取的实体。",10.0,18
6,"IMAGE_21","Original Training Set (Original)","original是从image_21中提取的实体。",10.0,15
7,"IMAGE_21","Negative Augmentation (+ Negative)","+ negative是从image_21中提取的实体。",10.0,14
8,"IMAGE_20","XLNet+DSC","XLNet+DSC是从image_20中提取的实体。",10.0,14
9,"IMAGE_21","Negative Downsampling (- Negative)","- negative是从image_21中提取的实体。",10.0,14
10,"Combined Positive and Negative Augmentation (+ Positive & Negative)","IMAGE_21","+ positive & negative是从image_21中提取的实体。",10.0,14
11,"IMAGE_21","Positive Augmentation (+ Positive)","+ positive是从image_21中提取的实体。",10.0,14
12,"IMAGE_21","TABLE 8","IMAGE_21" is the image of "TABLE 8".,10.0,13
13,"F1 SCORE","IMAGE_5","F1是从image_5中提取的实体。",10.0,9
14,"SCORE (F1-score)","TABLE 10",""The table displays multiple score values across its cells, linked to specific α values and benchmarks."",9.0,8
15,"IMAGE_23","SCORE (F1-score)","Score是从image_23中提取的实体。",10.0,7
    ```
    -----Sources-----
    ```csv
    id,content
    ```
    

### Initial LLM Response

Based on the provided data:

- The **XLNet+DSC** model variant achieves an **F1 score of 72.90 on the QuoRef dataset**, which represents an **improvement of +1.41** over the base **XLNet** model.

No other XLNet variants or their corresponding improvements on QuoRef are mentioned in the data tables. Therefore, **XLNet+DSC** is the only documented variant with a reported improvement on QuoRef, and it has the **highest (and only specified) improvement of +1.41 F1 points** compared to the base XLNet model.

### Commentary:
- The improvement stems from applying **Discriminative Self-Consistency (DSC)** to the XLNet architecture.
- DSC appears to be particularly effective on challenging datasets like QuoRef, which involves complex reasoning in machine reading comprehension.
- Since no other XLNet-based variants (e.g., XLNet+FL, XLNet+DL) are reported for QuoRef in the provided data, **XLNet+DSC stands as the top-performing variant by default** within the available evidence.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_21.jpg
**Response**: **Table Analysis**

The provided table (referred to as **IMAGE_21**, corresponding to **Table 8**) contains F1-score results for the **QQP dataset**, not the **QuoRef dataset**. It compares four model variants—BERT, BERT+FL, BERT+DL, and BERT+DSC—under various data augmentation strategies: original, +positive, +negative, -negative, and +positive & negative.

Key observations from this table:
- The **BERT+DSC** variant achieves the highest F1 score (**93.63**) under the "+ positive & negative" augmentation strategy.
- Relative improvements over the base BERT model are shown in parentheses (e.g., BERT+DSC improves by +0.81 in the original setting).
- However, this table is specific to the **QQP dataset**, not QuoRef.

**Image Analysis**

The image content confirms that it is **Table 8**, which focuses on **QQP** and does not include any data related to the **QuoRef** dataset. Therefore, no relevant information about QuoRef can be extracted from this image.

**Additional Context from Entities**

From the entity list:
- **XLNet+DSC** is mentioned as achieving high performance on multiple datasets, including **QuoRef**, with an F1 score of **72.90**, representing a **+1.41 improvement** over the base XLNet model.
- This information comes from the description of **XLNet+DSC** in the entities, which explicitly states its performance gains across tasks, including QuoRef.

**Integrated Insights**

To answer the query: *"Which model variant has the highest improvement in F1 score for the QuoRef dataset when compared to the base XLNet model?"*

- The **QuoRef dataset** is not present in **Table 8** (IMAGE_21), so this table cannot be used directly.
- However, the **entity description for XLNet+DSC** provides explicit information about performance on QuoRef: it reports an F1 score of **72.90**, which is **+1.41 higher** than the base XLNet model.
- No other XLNet variants are mentioned in the context of QuoRef, and no other models are reported with comparable improvements on this dataset in the provided data.

**Conclusion**

Based on the available information:

> The **XLNet+DSC** model variant has the highest improvement in F1 score for the **QuoRef dataset**, achieving a **+1.41 increase** over the base XLNet model.

This conclusion relies on the **entity description** of **XLNet+DSC**, not on the table or image, since the table pertains to QQP, not QuoRef.

### Merged Multimodal Response

The **XLNet+DSC** model variant achieves the highest improvement in F1 score for the **QuoRef dataset**, with a **+1.41** increase over the base XLNet model, reaching an F1 score of **72.90**. This information is derived from the entity description of XLNet+DSC, as the provided table (Table 8 / IMAGE_21) pertains to the QQP dataset and does not include QuoRef results. No other XLNet variants are reported to outperform this improvement on QuoRef in the given context.

### Final Response

The **XLNet+DSC** model variant achieves the highest improvement in F1 score for the **QuoRef dataset**, with a **+1.41** increase over the base XLNet model, reaching an F1 score of **72.90**. This is the only XLNet variant reported to show improvement on QuoRef in the provided data, making it the top-performing variant by default. The improvement is attributed to the application of **Discriminative Self-Consistency (DSC)**, which enhances performance on complex reasoning tasks like those in QuoRef.

---

## Query: What data augmentation method resulted in the highest F1-score for the BERT model according to Table 8?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"SCORE (F1-score)","OBJECT","Numerical performance metrics representing F1-scores across different experimental conditions and datasets. Higher SCORE values indicate better model performance in tasks such as question answering (QQP), named entity recognition (Chinese OntoNotes4.0), and machine reading comprehension (English QuoRef). The scores are reported in tables comparing baseline models (e.g., BERT) with variants using different loss functions (e.g., Dice Loss, DSC) and data augmentation strategies (+positive, +negative, etc.). For instance, in Table 8, BERT+DSC achieves the highest F1-score of 93.63 under the '+ positive & negative' augmentation setting, while in Table 10, the highest scores are 84.67 (Chinese Onto4.0) and 68.44 (English QuoRef) at specific α values.",2
1,"TABLE 8","EVENT","Table 8 presents experimental results comparing different data augmentation strategies for the Quora Question Pairs (QQP) dataset in terms of F1-score across multiple BERT-based model variants.",3
2,"IMAGE_21","ORI_IMG","IMAGE_21 is a table titled "Table 8: The effect of different data augmentation ways for QQP in terms of F1-score," which presents a comparative analysis of F1-scores across four model configurations—BERT, BERT+FL, BERT+DL, and BERT+DSC—under five distinct data augmentation strategies: 'original', '+ positive', '+ negative', '- negative', and '+ positive & negative'. The table demonstrates how each augmentation approach affects model performance on the Quora Question Pairs (QQP) dataset.

For the base BERT model, the original F1-score is 91.3. Adding only positive examples (+ positive) improves performance to 92.27, while adding only negative examples (+ negative) reduces it to 90.08. Removing negative examples (- negative), which results in a balanced 50-50 class distribution by down-sampling negatives, further decreases performance to 89.73. In contrast, combining both positive and negative augmentations (+ positive & negative) yields the highest score of 93.14.

Similar trends are observed across the enhanced models. BERT+FL achieves an original score of 91.86 (+0.56 over BERT), with its best result (93.45, +0.31 over its own baseline) under the '+ positive & negative' condition. BERT+DL starts at 91.92 (+0.62) and peaks at 93.52 (+0.38) with combined augmentation. BERT+DSC shows the highest baseline at 92.11 (+0.81) and reaches 93.63 (+0.49) with '+ positive & negative'.

Across all models, the '+ positive & negative' strategy consistently delivers the highest F1-scores, with improvements ranging from +0.31 to +0.49 relative to each model’s original performance. Conversely, '+ negative' generally degrades performance—attributed to creating a highly imbalanced dataset (21% positive, 79% negative)—and '- negative', despite balancing the class distribution, also underperforms compared to the original setup, particularly for the base BERT model. The table thus highlights that strategic combination of both positive and negative data augmentation yields optimal results, whereas isolated or removal-based strategies tend to be",10
3,"F1","OBJECT","F1 score is the harmonic mean of precision and recall, providing a single balanced metric to evaluate model performance in tasks such as Named Entity Recognition and Part-of-Speech tagging. It is especially useful when dealing with imbalanced datasets, as it accounts for both false positives and false negatives. In the experimental results, F1 scores are used as the primary indicator of model effectiveness, with improvements from variants like BERT-MRC+DSC reported as absolute gains (e.g., '+2.36') over baseline models.",1
4,"BERT+FL","ORGANIZATION","BERT+FL is an enhanced version of BERT-TAGGER that incorporates Focal Loss (FL), a technique originally proposed by Lin et al. (2017) to address class imbalance by down-weighting well-classified examples. This modification improves the F1 score on CTB5 to 96.76, representing a +0.70 gain over the base BERT-TAGGER, by focusing training more on hard-to-classify instances.",17
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,""BERT (DEVLIN ET AL., 2018)"","BERT+FL","BERT+FL is an enhancement of BERT-Tagger with feature learning techniques.",8.0,49
1,"BERT+FL","QUOREF","BERT+FL improved upon BERT with EM of 60.78 and F1 of 66.19 on QuoRef.",7.0,38
2,""BERT (DEVLIN ET AL., 2018)"","TABLE 8",""BERT and its variants (e.g., BERT+FL, BERT+DL) are evaluated in Table 8 using different data augmentation methods on the QQP dataset."",9.0,35
3,"BERT+FL","SQUAD V1.1","BERT+FL improved upon BERT with EM of 84.67 and F1 of 91.25 on SQuAD v1.1.",8.0,32
4,"BERT+FL","CTB5","BERT+FL is evaluated on the CTB5 dataset.",7.0,31
5,"BERT+FL","IMAGE_19","BERT+FL是从image_19中提取的实体。",10.0,30
6,"BERT+DSC","IMAGE_21","BERT+DSC是从image_21中提取的实体。",10.0,30
7,"BERT+DL","IMAGE_21","BERT+DL是从image_21中提取的实体。",10.0,30
8,"BERT+FL","IMAGE_20","BERT+FL是从image_20中提取的实体。",10.0,30
9,"BERT+FL","IMAGE_16","BERT+FL是从image_16中提取的实体。",10.0,30
10,"BERT+FL","UD1.4","BERT+FL is evaluated on the UD1.4 dataset.",7.0,29
11,"BERT+FL","SQUAD V2.0","BERT+FL improved upon BERT with EM of 78.92 and F1 of 82.20 on SQuAD v2.0.",7.0,29
12,"BERT+FL","IMAGE_21","BERT+FL是从image_21中提取的实体。",10.0,27
13,"BERT+FL","CTB6","BERT+FL is evaluated on the CTB6 dataset.",7.0,27
14,"BERT+CE","BERT+FL",""BERT+FL is an extension of BERT with additional fine-tuning or learning strategy, improving performance slightly."",8.0,26
15,"BERT+FL","Original Training Set (Original)","BERT+FL performs better than the original BERT under the same condition.",7.0,22
16,"BERT+FL","Combined Positive and Negative Augmentation (+ Positive & Negative)","BERT+FL achieves its best performance when both positive and negative samples are included.",9.0,21
17,"BERT+FL","Positive Augmentation (+ Positive)","BERT+FL improves performance when positive samples are added.",8.0,21
18,"BERT+FL","Negative Downsampling (- Negative)","BERT+FL benefits slightly from removing negative samples.",6.0,21
19,"BERT+FL","Negative Augmentation (+ Negative)","BERT+FL performs worse than original when negative samples are added.",5.0,21
20,"BERT+CE","IMAGE_21","BERT是从image_21中提取的实体。",10.0,19
21,"F1","IMAGE_18","F1是从image_18中提取的实体。",10.0,18
22,"IMAGE_21","Original Training Set (Original)","original是从image_21中提取的实体。",10.0,15
23,"IMAGE_21","Negative Augmentation (+ Negative)","+ negative是从image_21中提取的实体。",10.0,14
24,"IMAGE_21","Negative Downsampling (- Negative)","- negative是从image_21中提取的实体。",10.0,14
25,"IMAGE_21","Positive Augmentation (+ Positive)","+ positive是从image_21中提取的实体。",10.0,14
26,"Combined Positive and Negative Augmentation (+ Positive & Negative)","IMAGE_21","+ positive & negative是从image_21中提取的实体。",10.0,14
27,"IMAGE_21","TABLE 8","IMAGE_21" is the image of "TABLE 8".,10.0,13
28,"QQP","TABLE 8","Table 8 specifically reports results for data augmentation experiments conducted on the QQP dataset.",10.0,8
29,"SCORE (F1-score)","TABLE 10",""The table displays multiple score values across its cells, linked to specific α values and benchmarks."",9.0,8
30,"IMAGE_23","SCORE (F1-score)","Score是从image_23中提取的实体。",10.0,7
    ```
    -----Sources-----
    ```csv
    id,content
0,"we used Spacy1 to retrieve entity mentions and replace them with new ones by linking mentions to their corresponding entities in DBpedia. The augmented set contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

• Negative augmentation ( $\cdot +$ negative) We created a more imbalanced dataset. The size of the newly constructed training set and the data augmented technique are exactly the same as +negative, except that we chose negative training examples as templates. The augmented training set contains 458,477 examples, with $21 \%$ being positive and $79 \%$ being negative.

Table 8: The effect of different data augmentation ways for QQP in terms of F1-score.   

<table><tr><td></td><td>original</td><td>+ positive</td><td> + negative</td><td> - negative</td><td>+ positive &amp; negative</td></tr><tr><td>BERT</td><td>91.3</td><td>92.27</td><td>90.08</td><td>89.73</td><td>93.14</td></tr><tr><td>BERT+FL</td><td>91.86(+0.56)</td><td>92.64(+0.37)</td><td>90.61(+0.53)</td><td>90.79(+1.06)</td><td>93.45(+0.31)</td></tr><tr><td>BERT+DL</td><td>91.92(+0.62)</td><td>92.87(+0.60)</td><td>90.22(+0.14)</td><td>90.49(+0.76)</td><td>93.52(+0.38)</td></tr><tr><td>BERT+DSC</td><td>92.11(+0.81)</td><td>92.92(+0.65)</td><td>90.78(+0.70)</td><td>90.80(+1.07)</td><td>93.63(+0.49)</td></tr></table>

# • Negative downsampling (- negative)

We down-sampled negative examples in the original training set to get a balanced training set. The down-sampled set contains 269,165 examples, with $50 \%$ being positive and $50 \%$ being negative.

# • Positive and negative augmentation $^ +$ positive $\pmb { \& }$ +negative)

We augmented the original training data with additional positive and negative examples with the data distribution staying the same. The augmented dataset contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

Results are shown in Table 8. We first look at the first line, with all results obtained using the MLE objective. We can see that $^ +$ positive outperforms original, and +negative underperforms original. This is in line with our expectation since $^ +$ positive creates a balanced dataset while +negative creates a more imbalanced dataset. Despite the fact that -negative creates a balanced dataset, the number of training data decreases, resulting in inferior performances.

DSC achieves the highest F1 score across all datasets. Specially, for $^ +$ positive, DSC achieves minor improvements $\left( + 0 . 0 5 \mathrm { F 1 } \right.$ ) over DL. In contrast, it significantly outperforms DL for $^ +$ negative dataset. This is in line with our expectation since DSC helps more on more imbalanced datasets. The performance of FL and DL are not consistent across different datasets, while DSC consistently performs the best on all datasets.

# 5.2 Dice loss for accuracy-oriented tasks?

We argue that the cross-entropy objective is actually accuracy-oriented, whereas the proposed losses perform as a soft version of F1 score. To explore the effect of the dice loss on accuracyoriented tasks such as text classification, we conduct experiments on the Stanford Sentiment Treebank (SST) datasets including SST-2 and SST-5. We fine-tuned $\mathrm { B E R T _ { L a r g e } }$ with different training objectives. Experimental results for SST are shown in Table 9. For SST-5, BERT with CE achieves 55.57 in terms of accuracy, while DL and DSC perform slightly worse (54.63 and 55.19, respectively). Similar phenomenon is observed for SST-2. These results verify that the proposed dice loss is not accuracy-oriented, and should not be used for accuracy-oriented tasks.

<table><tr><td></td><td>SST-2</td><td>SST-5</td></tr><tr><td>Model</td><td>Acc</td><td>Acc</td></tr><tr><td>BERT+CE</td><td>94.90</td><td>55.57</td></tr><tr><td>BERT+DL</td><td>94.37</td><td>54.63</td></tr><tr><td>BERT+DSC</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling"
    ```
    

### Initial LLM Response

According to **Table 8**, the data augmentation method that resulted in the **highest F1-score for the base BERT model** was:

### **"+ positive & negative"**

- **F1-score**: **93.14**
- This represents an improvement of **+1.84** over the original BERT score of **91.30**.

### Commentary:
The "+ positive & negative" strategy involved augmenting the original training data with **both additional positive and negative examples**, while maintaining a **balanced class distribution (50% positive, 50% negative)**. This contrasts with other methods:
- **"+ positive"** also improved performance (92.27), but less than the combined approach.
- **"+ negative"** degraded performance (90.08), likely due to increased class imbalance (21% positive, 79% negative).
- **"- negative"** (downsampling negatives to balance classes) reduced overall data size and led to worse performance (89.73).

Thus, **combining both positive and negative augmentations** yielded optimal results for BERT on the QQP dataset in terms of F1-score.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_21.jpg
**Response**: ### Table Analysis

The provided table, identified as **Table 8**, presents the F1-scores of various BERT-based models under different data augmentation strategies on the Quora Question Pairs (QQP) dataset. The augmentation methods evaluated are:

- **original**: No augmentation.
- **+ positive**: Augmentation with additional positive examples.
- **+ negative**: Augmentation with additional negative examples.
- **- negative**: Downsampling of negative examples to balance the dataset.
- **+ positive & negative**: Augmentation with both positive and negative examples.

For the **BERT** model (first row), the F1-scores across these conditions are:
- **original**: 91.3
- **+ positive**: 92.27
- **+ negative**: 90.08
- **- negative**: 89.73
- **+ positive & negative**: **93.14**

Among these, the highest F1-score is **93.14**, achieved under the **+ positive & negative** augmentation method.

### Image Analysis

The image (`IMAGE_21`) corresponds directly to **Table 8**, as confirmed by the relationship `IMAGE_21 → TABLE 8`. The visual content of the image includes the same tabular data described above, with clear labeling of columns and rows. The values in the image match those in the provided table, confirming its accuracy and relevance.

Additionally, the image contains textual annotations describing the data augmentation techniques:
- **+ positive**: Adds positive examples, resulting in a balanced dataset (50% positive, 50% negative).
- **+ negative**: Adds negative examples, creating an imbalanced dataset (21% positive, 79% negative).
- **- negative**: Removes negative examples via downsampling to achieve balance (50% each).
- **+ positive & negative**: Combines both types of augmentation while maintaining the original class distribution.

These descriptions support the interpretation that **+ positive & negative** combines the benefits of both augmentations without introducing imbalance or reducing data size.

### Integrated Insights

The **+ positive & negative** augmentation strategy consistently yields the highest F1-score for all BERT variants, including the base BERT model. For BERT specifically, this method results in a **93.14 F1-score**, which is **1.84 points higher** than the original baseline (91.3). This improvement surpasses all other augmentation methods, including **+ positive** (92.27) and **+ negative** (90.08).

Moreover, the **+ negative** method degrades performance due to severe class imbalance, while **- negative** reduces training data volume despite balancing classes, leading to suboptimal results. In contrast, **+ positive & negative** maintains balanced class distribution and increases training data size, enabling better generalization.

### Conclusion

According to **Table 8** (and its corresponding image `IMAGE_21`), the **+ positive & negative** data augmentation method resulted in the **highest F1-score (93.14)** for the **BERT model**. This strategy outperforms all others by effectively leveraging both positive and negative examples without introducing imbalance or data loss.

### Merged Multimodal Response

According to Table 8, the **+ positive & negative** data augmentation method resulted in the highest F1-score for the BERT model, achieving a score of **93.14**. This approach combines both positive and negative example augmentation while preserving the original class distribution, leading to improved performance compared to other methods.

### Final Response

According to Table 8, the data augmentation method that resulted in the highest F1-score for the BERT model was **"+ positive & negative"**, achieving an F1-score of **93.14**. This approach augmented the training data with both additional positive and negative examples while maintaining a balanced class distribution (50% positive, 50% negative), leading to the best performance among all tested methods.

---

## Query: What is the highest F1 score achieved on the Chinese OntoNotes4.0 dataset, according to Table 10?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"SCORE (F1-score)","OBJECT","Numerical performance metrics representing F1-scores across different experimental conditions and datasets. Higher SCORE values indicate better model performance in tasks such as question answering (QQP), named entity recognition (Chinese OntoNotes4.0), and machine reading comprehension (English QuoRef). The scores are reported in tables comparing baseline models (e.g., BERT) with variants using different loss functions (e.g., Dice Loss, DSC) and data augmentation strategies (+positive, +negative, etc.). For instance, in Table 8, BERT+DSC achieves the highest F1-score of 93.63 under the '+ positive & negative' augmentation setting, while in Table 10, the highest scores are 84.67 (Chinese Onto4.0) and 68.44 (English QuoRef) at specific α values.",2
1,"CHINESE ONTONOTES4.0 NER DATASET",GEO,"Chinese OntoNotes4.0 is a named entity recognition dataset focused on Chinese language data, used in experiments evaluating the Tversky Index hyperparameters. In the image table, it appears as 'CHINESE ONTO4.0', showing scores that peak at 84.67 when α = 0.6.",4
2,"CHINESE ONTONOTES4.0","UNKNOWN","The data split for Chinese OntoNotes4.0 follows the approach used by Wu et al. (2019).",1
3,"F1 Score","UNKNOWN","The F1 score is the harmonic mean of precision and recall, providing a single metric that balances both concerns. It is computed as 2 × (Precision × Recall) / (Precision + Recall). The F1 score is equivalent to the Dice coefficient (DSC) when applied to binary classification or set similarity evaluation, and it is widely used to assess the performance of named entity recognition and part-of-speech tagging systems.",3
4,"F1","OBJECT","F1 score is the harmonic mean of precision and recall, providing a single balanced metric to evaluate model performance in tasks such as Named Entity Recognition and Part-of-Speech tagging. It is especially useful when dealing with imbalanced datasets, as it accounts for both false positives and false negatives. In the experimental results, F1 scores are used as the primary indicator of model effectiveness, with improvements from variants like BERT-MRC+DSC reported as absolute gains (e.g., '+2.36') over baseline models.",1
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"F1","IMAGE_18","F1是从image_18中提取的实体。",10.0,18
1,"F1 Score","IMAGE_17","F1是从image_17中提取的实体。",10.0,16
2,"CHINESE ONTONOTES4.0 NER DATASET","TABLE 10",""Table 10 contains experimental results specifically derived from the Chinese OntoNotes4.0 NER dataset, showing F1 scores at varying α values."",9.0,10
3,"CHINESE ONTONOTES4.0 NER DATASET","α (alpha)",""The value of α influences the performance score on the Chinese Onto4.0 benchmark, with the highest score (84.67) achieved at α = 0.6."",8.0,10
4,"CHINESE ONTONOTES4.0 NER DATASET","IMAGE_23","Chinese Onto4.0是从image_23中提取的实体。",10.0,9
5,"SCORE (F1-score)","TABLE 10",""The table displays multiple score values across its cells, linked to specific α values and benchmarks."",9.0,8
6,"CHINESE ONTONOTES4.0 NER DATASET","ENGLISH QUOREF MRC DATASET",""Both benchmarks are compared side by side in the table, allowing for direct comparison of performance across languages and α values."",7.0,8
7,"IMAGE_23","SCORE (F1-score)","Score是从image_23中提取的实体。",10.0,7
8,"F1 Score","Precision (Prec.)",""F1 score is derived from precision and recall, emphasizing their combined importance in model evaluation."",9.0,6
9,"F1 Score","Recall (Rec.)",""F1 score depends on recall, along with precision, to evaluate model performance comprehensively."",9.0,6
10,"CHINESE ONTONOTES4.0","WU ET AL.","The data split for Chinese OntoNotes4.0 follows the approach used by Wu et al. (2019).",8.0,2
    ```
    -----Sources-----
    ```csv
    id,content
0,"</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling the tradeoff between false-negatives and false-positives. In this subsection, we explore the effect of hyperparameters (i.e., $\alpha$ and $\beta$ ) in TI to test how they manipulate the tradeoff. We conduct experiments on the Chinese OntoNotes4.0 NER dataset and English QuoRef MRC dataset. Experimental results are shown in Table 10. The highest F1 on Chinese OntoNotes4.0 is 84.67 when $\alpha$ is set to 0.6 while for QuoRef, the highest F1 is 68.44 when $\alpha$ is set to 0.4. In addition, we can observe that the performance varies a lot as $\alpha$ changes in distinct datasets, which shows that the hyperparameters $\alpha , \beta$ acturally play an important role in TI.

# 6 Conclusion

In this paper, we propose the dice-based loss to narrow down the gap between training objective and evaluation metrics (F1 score). Experimental results show that the proposed loss function help

<table><tr><td>α</td><td>Chinese Onto4.0</td><td>English QuoRef</td></tr><tr><td>α=0.1</td><td>80.13</td><td>63.23</td></tr><tr><td>α=0.2</td><td>81.17</td><td>63.45</td></tr><tr><td>α= 0.3</td><td>84.22</td><td>65.88</td></tr><tr><td>α=0.4</td><td>84.52</td><td>68.44</td></tr><tr><td>α=0.5</td><td>84.47</td><td>67.52</td></tr><tr><td>α=0.6</td><td>84.67</td><td>66.35</td></tr><tr><td>α=0.7</td><td>81.81</td><td>65.09</td></tr><tr><td>α=0.8</td><td>80.97</td><td>64.13</td></tr><tr><td>α= 0.9</td><td>80.21</td><td>64.84</td></tr></table>

Table 10: The effect of hyperparameters in Tversky Index. We set $\beta = 1 - \alpha$ and thus we only list $\alpha$ here.

to achieve significant performance boost without changing model architectures.

# Acknowledgement

We thank all anonymous reviewers, as well as Qinghong Han, Wei Wu and Jiawei Wu for their comments and suggestions. The work is supported by the National Natural Science Foundation of China (NSFC No. 61625107 and 61751209).

# References

Bernd Bohnet, Ryan T. McDonald, Gonc¸alo Simoes, ˜ Daniel Andor, Emily Pitler, and Joshua Maynez. 2018. Morphosyntactic tagging with a meta-bilstm model over context sensitive token encodings. In Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics, ACL 2018, Melbourne, Australia, July 15-20, 2018, Volume 1: Long Papers, pages 2642–2652.

Haw-Shiuan Chang, Erik G. Learned-Miller, and Andrew McCallum. 2017. Active bias: Training more accurate neural networks by emphasizing high variance samples. In NIPS.

N. V. Chawla, K. W. Bowyer, Lawrence O. Hall, and W. P. Kegelmeyer. 2002. Smote: Synthetic minority over-sampling technique. J. Artif. Intell. Res., 16:321– 357.

Danqi Chen, Adam Fisch, Jason Weston, and Antoine Bordes. 2017. Reading wikipedia to answer opendomain questions. arXiv preprint arXiv:1704.00051.

Kean Chen, Jianguo Li, Weiyao Lin, John See, Ji Wang, Lingyu Duan, Zhibo Chen, Changwei He, and Junni Zou. 2019. Towards accurate one-stage object detection with ap-loss. In IEEE Conference on Computer Vision and Pattern Recognition, CVPR 2019, Long Beach, CA, USA, June 16-20, 2019, pages 5119–5127.

Shijuan Chen, Haibo He, and Edwardo A. Garcia. 2010. Ramoboost: Ranked minority oversampling in boosting. IEEE Transactions on Neural Networks, 21:1624– 1642.

Kevin Clark, Minh-Thang Luong, Christopher D. Manning, and Quoc V. Le. 2018. Semi-supervised sequence modeling with cross-view training. In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Procfessing, Brussels, Belgium, October 31 - November 4, 2018, pages 191"
1,"2018. Chinese ner using lattice lstm. arXiv preprint arXiv:1805.02023.

# A Dataset Details

# A.1 Part-of-Speech Tagging

Datasets We conduct experiments on three widely used benchmark, i.e., Chinese Treebank $5 . 0 ^ { 2 } / 6 . 0 ^ { 3 }$ and $\mathrm { U D } 1 . 4 ^ { 4 }$ .

• CTB5 is a Chinese dataset for tagging and parsing, which contains 507,222 words, 824,983 characters and 18,782 sentences extracted from newswire sources, including 698 articles from Xinhua (1994-1998), 55 articles from Information Services Department of HKSAR (1997) and 132 articles from Sinorama Magazine (1996-1998 & 2000-2001).

• CTB6 is an extension of CTB5, containing 781,351 words, 1,285,149 characters and 28,295 sentences.

• UD is the abbreviation of Universal Dependencies, which is a framework for consistent annotation of grammar (parts of speech, morphological features, and syntactic dependencies) across different human languages. In this work, we use UD1.4 for Chinese POS tagging.

# A.2 Named Entity Recognition

Datasets For the NER task, we consider both Chinese datasets, i.e., OntoNotes $4 . 0 ^ { 5 }$ and MSRA6 , and English datasets, i.e., CoNLL2003 7 and OntoNote $5 . 0 ^ { 8 }$ .

• CoNLL2003 is an English dataset with 4 entity types: Location, Organization, Person and Miscellaneous. We followed data processing protocols in (Ma and Hovy, 2016).

• English OntoNotes5.0 consists of texts from a wide variety of sources and contains 18 entity types. We use the standard train/dev/test split of CoNLL2012 shared task.

• Chinese MSRA performs as a Chinese benchmark dataset containing 3 entity types. Data in MSRA is collected from news domain. Since the development set is not provided in the original MSRA dataset, we randomly split the training set into training and development splits by 9:1. We use the official test set for evaluation.

• Chinese OntoNotes4.0 is a Chinese dataset and consists of texts from news domain, which has 18 entity types. In this paper, we take the same data split as Wu et al. (2019) did.

# A.3 Machine Reading Comprephension

Datasets For MRC task, we use three datasets: $\mathrm { S Q u A D v 1 . 1 / v 2 . 0 ^ { 9 } }$ and Queref10 datasets.

• SQuAD v1.1 and SQuAD $\mathbf { v } 2 . \mathbf { 0 }$ are the most widely used QA benchmarks. SQuAD1.1 is a collection of 100K crowdsourced question-answer pairs, and SQuAD2.0 extends SQuAD1.1 allowing no short answer exists in the provided passage.

• Quoref is a QA dataset which tests the coreferential reasoning capability of reading comprehension systems, containing 24K questions over 4.7K paragraphs from Wikipedia.

# A.4 Paraphrase Identification

Datasets Experiments are conducted on two PI datasets: $\mathbf { M R P C } ^ { 1 1 }$ and $\mathrm { Q Q P ^ { 1 2 } }$ .

• MRPC is a corpus of sentence pairs automatically extracted from online news sources, with human annotations of whether the sentence pairs are semantically equivalent. The MRPC dataset has imbalanced classes (6800 pairs in total, and $68 \%$ for positive, $32 \%$ for negative).

QQP is a collection of question pairs from the community question-answering website Quora. The class distribution in QQP is also unbalanced (over 400,000 question pairs in total, and $37 \%$ for positive, $63 \%$ for negative)."
    ```
    

### Initial LLM Response

According to **Table 10**, the **highest F1 score** achieved on the **Chinese OntoNotes4.0 NER dataset** is **84.67**, which occurs when the Tversky Index hyperparameter **α = 0.6**.

This result is part of an experiment evaluating the effect of the α hyperparameter in the Tversky Index (with β set to 1 − α). The scores across different α values show that performance peaks at α = 0.6 for this dataset, highlighting the sensitivity of model performance to the choice of α in imbalanced learning scenarios such as named entity recognition.

---

## Query: Which model achieved the highest F1 score in the English WSJ dataset?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"F1 SCORE",CONCEPT,"F1 Score, the harmonic mean of precision and recall, used to evaluate the performance of classification models. It is an F1-oriented statistic used to measure the similarity between two sets, commonly applied in evaluating model predictions against ground truth in machine learning contexts.",2
1,"F1","OBJECT","F1 score is the harmonic mean of precision and recall, providing a single balanced metric to evaluate model performance in tasks such as Named Entity Recognition and Part-of-Speech tagging. It is especially useful when dealing with imbalanced datasets, as it accounts for both false positives and false negatives. In the experimental results, F1 scores are used as the primary indicator of model effectiveness, with improvements from variants like BERT-MRC+DSC reported as absolute gains (e.g., '+2.36') over baseline models.",1
2,"SCORE (F1-score)","OBJECT","Numerical performance metrics representing F1-scores across different experimental conditions and datasets. Higher SCORE values indicate better model performance in tasks such as question answering (QQP), named entity recognition (Chinese OntoNotes4.0), and machine reading comprehension (English QuoRef). The scores are reported in tables comparing baseline models (e.g., BERT) with variants using different loss functions (e.g., Dice Loss, DSC) and data augmentation strategies (+positive, +negative, etc.). For instance, in Table 8, BERT+DSC achieves the highest F1-score of 93.63 under the '+ positive & negative' augmentation setting, while in Table 10, the highest scores are 84.67 (Chinese Onto4.0) and 68.44 (English QuoRef) at specific α values.",2
3,"F1 Score","UNKNOWN","The F1 score is the harmonic mean of precision and recall, providing a single metric that balances both concerns. It is computed as 2 × (Precision × Recall) / (Precision + Recall). The F1 score is equivalent to the Dice coefficient (DSC) when applied to binary classification or set similarity evaluation, and it is widely used to assess the performance of named entity recognition and part-of-speech tagging systems.",3
4,""BOHNET ET AL., 2018"",PERSON,Bohnet et al. (2018) are researchers who developed the Meta BiLSTM model evaluated on the English WSJ dataset.,2
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"DICE SIMILARITY COEFFICIENT (DSC)","F1 SCORE",""The Dice Similarity Coefficient (DSC) is equal to the F1 score, both representing the harmonic mean of precision and recall."",10.0,41
1,"F1","IMAGE_18","F1是从image_18中提取的实体。",10.0,18
2,"F1 Score","IMAGE_17","F1是从image_17中提取的实体。",10.0,16
3,""BOHNET ET AL., 2018"","IMAGE_17",""Bohnet et al., 2018是从image_17中提取的实体。"",10.0,15
4,"F1 SCORE","IMAGE_5","F1是从image_5中提取的实体。",10.0,9
5,"SCORE (F1-score)","TABLE 10",""The table displays multiple score values across its cells, linked to specific α values and benchmarks."",9.0,8
6,""BOHNET ET AL., 2018"","TABLE 4","The Meta BiLSTM model by Bohnet et al. (2018) is listed in Table 4 under results for the English WSJ dataset.",8.0,8
7,"IMAGE_23","SCORE (F1-score)","Score是从image_23中提取的实体。",10.0,7
8,"F1 Score","Precision (Prec.)",""F1 score is derived from precision and recall, emphasizing their combined importance in model evaluation."",9.0,6
9,"F1 Score","Recall (Rec.)",""F1 score depends on recall, along with precision, to evaluate model performance comprehensively."",9.0,6
    ```
    -----Sources-----
    ```csv
    id,content
0,"F1</td><td>Prec.</td><td>Rec.</td><td>F1</td><td>Prec.</td><td>Rec.</td><td>F1</td></tr><tr><td>Joint-POS(Sig)(Shao et al., 2017)</td><td>93.68</td><td>94.47</td><td>94.07</td><td>1</td><td>-</td><td>90.81</td><td>89.28</td><td>89.54</td><td>89.41</td></tr><tr><td>Joint-POS(Ens)(Shao et al., 2017)</td><td>93.95</td><td>94.81</td><td>94.38</td><td></td><td></td><td>1</td><td>89.67</td><td>89.86</td><td>89.75</td></tr><tr><td>Lattice-LSTM(Zhang and Yang, 2018)</td><td>94.77</td><td>95.51</td><td>95.14</td><td>92.00</td><td>90.86</td><td>91.43</td><td>90.47</td><td>89.70</td><td>90.09</td></tr><tr><td>BERT-Tagger(Devlin et al., 2018)</td><td>95.86</td><td>96.26</td><td>96.06</td><td>94.91</td><td>94.63</td><td>94.77</td><td>95.42</td><td>94.17</td><td>94.79</td></tr><tr><td>BERT+FL</td><td>96.11</td><td>97.42</td><td>96.76 (+0.70)</td><td>95.80</td><td>95.08</td><td>95.44 (+0.67)</td><td>96.33</td><td>95.85</td><td>96.81 (+2.02)</td></tr><tr><td>BERT+DL</td><td>96.77</td><td>98.87</td><td>97.81 (+1.75)</td><td>94.08</td><td>96.12</td><td>95.09 (+0.32)</td><td>96.10</td><td>97.79</td><td>96.94 (+2.15)</td></tr><tr><td>BERT+DSC</td><td>97.10</td><td>98.75</td><td>97.92 (+1.86)</td><td>96.29</td><td>96.85</td><td>96.57 (+1.80)</td><td>96.24</td><td>97.73</td><td>96.98 (+2.19)</td></tr></table>

Table 3: Experimental results for Chinese POS datasets including CTB5, CTB6 and UD1.4.

Table 4: Experimental results for English POS datasets.   

<table><tr><td>English WSJ</td><td></td><td></td><td></td></tr><tr><td>Model Meta BiLSTM(Bohnet et al.,2018)</td><td>Prec. 1</td><td>Rec. 1</td><td>F1 98.23</td></tr><tr><td>BERT-Tagger (Devlin et al., 2018)</td><td>99.21</td><td>98.36</td><td>98.86</td></tr><tr><td>BERT-Tagger+FL</td><td>98.36</td><td>98.97</td><td>98.88 (+0.02)</td></tr><tr><td>BERT-Tagger+DL</td><td>99.34</td><td>98.22</td><td>98.91 (+0.05)</td></tr><tr><td>BERT-Tagger+DSC</td><td>99.41</td><td>98.93</td><td>99.38 (+0.52)</td></tr><tr><td colspan="4">English Tweets</td></tr><tr><td>Model</td><td>Prec.</td><td>Rec.</td><td>F1</td></tr><tr><td>FastText+CNN+CRF(Godin, 2019) BERT-Tagger (Devlin et al.,2018)</td><td>- 92.33</td><td>- 91.98</td><td>91.78 92.34</td></tr><tr><td>BERT-Tagger+FL</td><td>91.24</td><td>93.22</td><td>92.47 (+0.13)</td></tr><tr><td>BERT-Tagger+DL</td><td>91.44</td><td>92.88</td><td>92.52 (+0.18)</td></tr><tr><td>BERT-Tagger+DSC</td><td>92.87"
    ```
    

### Initial LLM Response

### Highest F1 Score on the English WSJ Dataset

Based on **Table 4** from the provided data (as referenced in the *Sources* and linked via relationships to *"BOHNET ET AL., 2018"* and various model entries), the **English WSJ dataset** results include the following models and their F1 scores:

| Model                              | F1 Score |
|-----------------------------------|----------|
| Meta BiLSTM (Bohnet et al., 2018) | 98.23    |
| BERT-Tagger (Devlin et al., 2018) | 98.86    |
| BERT-Tagger + FL                  | 98.88 (+0.02) |
| BERT-Tagger + DL                  | 98.91 (+0.05) |
| **BERT-Tagger + DSC**             | **99.38 (+0.52)** |

> **Note**: The values in parentheses (e.g., +0.52) indicate absolute improvement over the baseline BERT-Tagger.

### Conclusion

The **BERT-Tagger + DSC** model achieved the **highest F1 score of 99.38** on the English WSJ dataset, outperforming all other listed models, including the original BERT-Tagger and the Meta BiLSTM by Bohnet et al. (2018).

This result highlights the effectiveness of incorporating the **Dice Similarity Coefficient (DSC)** as a loss function (or optimization target), which—given its equivalence to the F1 score—directly optimizes for this evaluation metric.

---

## Query: What performance boost did BERT+DSC achieve for the MRPC?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"MRPC F1","EVENT","MRPC F1 refers to the F1 score used to evaluate model performance on the Microsoft Research Paraphrase Corpus (MRPC) task, which assesses a system's ability to determine whether two sentences are paraphrases of each other. In the experiments, BERT+DSC achieves 88.92 F1 and XLNet+DSC reaches 89.78 F1, representing significant improvements over their base models.",1
1,"BERT-MRC+DSC","ORGANIZATION","BERT-MRC+DSC is a variant of BERT-MRC that employs Dynamic Self-Criticism (DSC) during training to refine predictions by reducing the model's focus on already-correct examples. This method yields the most significant performance improvements among the evaluated enhancements, achieving state-of-the-art results on multiple NER benchmarks: +0.29 F1 on CoNLL 2003, +0.96 on OntoNotes5.0, +0.69 on Chinese MSRA, and +2.36 on Chinese OntoNotes 4.0. The DSC loss function stabilizes training by attenuating gradients once prediction confidence exceeds a threshold (e.g., probability > 0.5), leading to more robust and balanced learning.",5
2,"IMAGE_20","ORI_IMG",""The image is a table labeled 'Table 7: Experimental results for PI task.' It presents performance comparisons of various models on two natural language understanding benchmarks: MRPC (Microsoft Research Paraphrase Corpus) and QQP (Quora Question Pairs). The table has three columns: 'Model', 'MRPC F1', and 'QQP F1'. Each row corresponds to a model configuration, with the base models being BERT (Devlin et al., 2018) and XLNet (Yang et al., 2019), followed by their variants enhanced with different techniques: FL (Focal Loss), DL (Denoising Loss), and DSC (Dual Soft Constraint loss).The first section lists BERT-based models. BERT achieves an F1 score of 88.0 on MRPC and 91.3 on QQP. Adding FL improves the scores to 88.43 (+0.43) and 91.86 (+0.56), respectively. BERT+DL yields 88.71 (+0.71) and 91.92 (+0.62). The best-performing BERT variant is BERT+DSC, achieving 88.92 (+0.92) on MRPC and 92.11 (+0.81) on QQP.The second section presents XLNet-based models. XLNet alone achieves 89.2 on MRPC and 91.8 on QQP. With FL, it improves to 89.25 (+0.05) and 92.31 (+0.51). XLNet+DL reaches 89.33 (+0.13) and 92.39 (+0.59). The top-performing model in this group is XLNet+DSC, scoring 89.78 (+0.58) on MRPC and 92.60 (+0.79) on QQP.All values are presented in black text on a white background, with clear horizontal lines separating rows. The table uses bold formatting for the highest scores in each column (BERT+DSC and XLNet+DSC). The improvement values in parentheses indicate absolute gains over the base model. The overall trend shows that the DSC method consistently provides the largest performance boost across both datasets and base models, suggesting its effectiveness in enhancing model performance on paraphrase identification tasks."",13
3,"LI","PERSON",""Lead author of the BERT-MRC model (2019), whose work forms the backbone of the current NER implementation."",1
4,"XLNET+DSC",ORGANIZATION,"An enhanced version of XLNet with DSC (Discriminative Self-Correction), achieving EM of 89.79 and F1 of 95.77 on SQuAD v1.1, EM of 87.65 and F1 of 89.51 on SQuAD v2.0, and EM of 65.98 and F1 of 72.90 on QuoRef. DSC refers to a proposed loss function or training objective that enhances model performance in both MRC and PI tasks when combined with BERT or XLNet.",4
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"BERT+DSC","IMAGE_20","BERT+DSC是从image_20中提取的实体。",10.0,33
1,"BERT+DL","IMAGE_20","BERT+DL是从image_20中提取的实体。",10.0,33
2,"BERT+FL","IMAGE_20","BERT+FL是从image_20中提取的实体。",10.0,30
3,"QUOREF","XLNET+DSC","XLNet+DSC improved upon XLNet with EM of 65.98 and F1 of 72.90 on QuoRef.",8.0,25
4,"BERT-MRC+DSC","IMAGE_18","BERT-MRC+DSC是从image_18中提取的实体。",10.0,22
5,"BERT+CE","IMAGE_20","BERT是从image_20中提取的实体。",10.0,22
6,"SQUAD V1.1","XLNET+DSC","XLNet+DSC improved upon XLNet with EM of 89.79 and F1 of 95.77 on SQuAD v1.1.",9.0,19
7,"IMAGE_20","XLNet+DL","XLNet+DL是从image_20中提取的实体。",10.0,18
8,"IMAGE_20","XLNet+FL","XLNet+FL是从image_20中提取的实体。",10.0,18
9,"BERT-MRC+DSC","CHINESE MSRA","BERT-MRC+DSC achieves the best performance on Chinese MSRA with an F1 of 96.72.",9.0,18
10,"IMAGE_19","XLNET+DSC","XLNet+DSC是从image_19中提取的实体。",10.0,17
11,"SQUAD V2.0","XLNET+DSC","XLNet+DSC improved upon XLNet with EM of 87.65 and F1 of 89.51 on SQuAD v2.0.",8.0,16
12,"IMAGE_20","TABLE 7","IMAGE_20" is the image of "TABLE 7".,10.0,15
13,"IMAGE_20","MRPC F1","MRPC F1是从image_20中提取的实体。",10.0,14
14,"IMAGE_20",""Yang et al., 2019"",""Yang et al., 2019是从image_20中提取的实体。"",10.0,14
15,"IMAGE_20","QQP F1","QQP F1是从image_20中提取的实体。",10.0,14
16,"IMAGE_20","XLNET","XLNet是从image_20中提取的实体。",10.0,14
17,""DEVLIN ET AL., 2018"","IMAGE_20",""Devlin et al., 2018是从image_20中提取的实体。"",10.0,14
18,"IMAGE_20","XLNet+DSC","XLNet+DSC是从image_20中提取的实体。",10.0,14
19,"BERT-MRC+DSC","CHINESE ONTONOTES 4.0","BERT-MRC+DSC achieves the highest F1 of 84.47 on Chinese OntoNotes 4.0.",9.0,14
20,"BERT-MRC+DSC","ENGLISH CONLL 2003","BERT-MRC+DSC achieves the best result on English CoNLL 2003 with an F1 of 93.33.",9.0,14
21,"BERT-MRC+DSC","ENGLISH ONTONOTES5.0","BERT-MRC+DSC achieves the highest F1 of 92.07 on English OntoNotes 5.0.",9.0,13
22,""BERT-MRC (LI ET AL., 2019)"","LI","Li is the lead author of the BERT-MRC model published in 2019.",10.0,11
    ```
    -----Sources-----
    ```csv
    id,content
0,".8</td></tr><tr><td>BERT-Tagger (Devlin et al., 2018)</td><td>90.01</td><td>88.35</td><td>89.16</td></tr><tr><td>BERT-MRC(Li et al., 2019)</td><td>92.98 89.95</td><td></td><td>91.11 91.22</td></tr><tr><td>BERT-MRC+FL</td><td>90.13</td><td>92.34</td><td>(+0.11)</td></tr><tr><td>BERT-MRC+DL</td><td>91.7092.06</td><td></td><td>91.88 (+0.77)</td></tr><tr><td>BERT-MRC+DSC</td><td>91.59</td><td>92.56</td><td>92.07 (+0.96)</td></tr><tr><td colspan="4">Chinese MSRA</td></tr><tr><td>Model</td><td>Prec.</td><td>Rec.</td><td>F1</td></tr><tr><td>Lattice-LSTM (Zhang and Yang, 2018)</td><td>93.57</td><td>92.79</td><td>93.18</td></tr><tr><td>BERT-Tagger (Devlin et al., 2018)</td><td>94.97</td><td>94.62</td><td>94.80</td></tr><tr><td>Glyce-BERT (Wu et al.,2019)</td><td>95.57</td><td>95.51</td><td>95.54</td></tr><tr><td>BERT-MRC(Li et al., 2019)</td><td>96.18</td><td>95.12</td><td>95.75</td></tr><tr><td>BERT-MRC+FL</td><td>95.45</td><td>95.89</td><td>95.67</td></tr><tr><td>BERT-MRC+DL</td><td>96.2096.68</td><td></td><td>(-0.08) 96.44</td></tr><tr><td>BERT-MRC+DSC</td><td>96.67</td><td>96.77</td><td>(+0.69) 96.72</td></tr><tr><td></td><td></td><td></td><td>(+0.97)</td></tr><tr><td colspan="4">Chinese OntoNotes 4.0 Model</td></tr><tr><td></td><td>Prec.</td><td>Rec.</td><td>F1</td></tr><tr><td>Lattice-LSTM (Zhang and Yang, 2018)</td><td>76.35</td><td>71.56</td><td>73.88</td></tr><tr><td>BERT-Tagger (Devlin et al.,2018)</td><td>78.01</td><td>80.35</td><td>79.16</td></tr><tr><td>Glyce-BERT (Wu et al., 2019)</td><td>81.87</td><td>81.40</td><td>80.62</td></tr><tr><td>BERT-MRC(Li et al., 2019)</td><td>82.98</td><td>81.25</td><td>82.11 83.30</td></tr><tr><td>BERT-MRC+FL</td><td>83.63</td><td>82.97</td><td>(+1.19)</td></tr><tr><td>BERT-MRC+DL</td><td></td><td>83.9784.05</td><td>84.01 (+1.90)</td></tr><tr><td>BERT-MRC+DSC</td><td></td><td>84.2284.72</td><td>84.47 (+2.36)</td></tr></table>

# 4.2 Named Entity Recognition

Settings Named entity recognition (NER) is the task of detecting the span and semantic category of entities within a chunk of text. Our implementation uses the current state-of-the-art model proposed by Li et al. (2019) as the backbone, and changes the MLE loss to DSC loss. Datasets that we use include OntoNotes4.0 (Pradhan et al., 2011), MSRA (Levow, 2006), CoNLL2003 (Sang and Meulder, 2003) and OntoNotes5.0 (Pradhan et al., 2013). We report span-level micro-averaged precision, recall and F1.

Baselines We use the following baselines:

• ELMo: a tagging model with pretraining from Peters et al. (2018).   
• Lattice-LSTM: Zhang and Yang (2018) constructs a word-character lattice, only used in Chinese datasets.   
CVT: Clark et al. (2018) uses Cross-View Training(CVT) to improve the representations of a Bi-LSTM encoder.   
• Bert-Tagger: Devlin et"
    ```
    

### Initial LLM Response

BERT+DSC achieved a performance boost of **+0.92 F1 points** on the MRPC (Microsoft Research Paraphrase Corpus) task compared to the base BERT model.

- **Base BERT F1 score on MRPC**: 88.0  
- **BERT+DSC F1 score on MRPC**: 88.92  
- **Improvement**: **+0.92**

This improvement is the largest among the evaluated enhancements (FL, DL, and DSC) for BERT on this benchmark, as shown in Table 7 (IMAGE_20). The result underscores the effectiveness of the Dynamic Self-Criticism (DSC) training method in refining model predictions for paraphrase identification tasks.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_20.jpg
**Response**: ### Table Analysis

The provided table, labeled "Table 7: Experimental results for PI task," presents performance comparisons of various models on two natural language understanding benchmarks: MRPC (Microsoft Research Paraphrase Corpus) and QQP (Quora Question Pairs). The relevant row for the query is:

- **BERT+DSC**: Achieves an F1 score of **88.92** on MRPC.

This value is compared to the base BERT model (Devlin et al., 2018), which achieves an F1 score of **88.0** on MRPC.

The improvement is explicitly stated in parentheses as **(+0.92)**, indicating that BERT+DSC outperforms the base BERT model by **0.92 absolute points** in F1 score on the MRPC task.

### Image Analysis

The image corresponds directly to the table described above. It contains no additional visual annotations or elements beyond the tabular data. The text within the image confirms the values and relationships presented in the table, including the bold formatting used to highlight the highest scores in each column (e.g., BERT+DSC and XLNet+DSC).

### Integrated Insights

Based on the combined analysis of the table and the image:
- The **performance boost** achieved by **BERT+DSC** on the **MRPC task** is **+0.92 in F1 score** compared to the base BERT model.
- This improvement is consistent with the trend observed across both datasets (MRPC and QQP), where the DSC method consistently provides the largest gains over other enhancements like FL (Focal Loss) and DL (Denoising Loss).
- The **DSC (Dual Soft Constraint)** loss function appears to be particularly effective in refining model predictions, especially in tasks requiring fine-grained discrimination between paraphrases.

### Final Answer

BERT+DSC achieved a **+0.92 absolute improvement in F1 score** on the MRPC task compared to the base BERT model.

### Merged Multimodal Response

BERT+DSC achieved a **+0.92 absolute improvement in F1 score** on the MRPC task compared to the base BERT model (which scored 88.0, while BERT+DSC scored 88.92).

### Final Response

BERT+DSC achieved a **+0.92 absolute improvement in F1 score** on the MRPC (Microsoft Research Paraphrase Corpus) task compared to the base BERT model. Specifically:

- **Base BERT F1 score**: 88.0  
- **BERT+DSC F1 score**: 88.92  
- **Performance boost**: **+0.92 F1 points**

This improvement is the largest among the evaluated enhancements (FL, DL, and DSC) for BERT on this benchmark.

---

## Query: How does the performance of BERT+DL on SST-5 compare to that of BERT+DSC?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"BERT+DSC",ORGANIZATION,"A model configuration combining BERT with Deep Supervision Classification, achieving 94.84% accuracy on SST-2 and 55.19% on SST-5. This matches the application of DSC (a proposed loss function or training objective) with BERT in experiments, including those reported in Table 9.",20
1,"BERT+CE",ORGANIZATION,"A model configuration combining BERT with Cross-Entropy loss, achieving 94.90% accuracy on SST-2 and 55.57% on SST-5. This corresponds to the BERT model fine-tuned with cross-entropy as referenced in Table 9 for sentiment classification tasks.",9
2,"TABLE 9","EVENT",""Table 9 displays the performance of BERT models with different loss functions (CE, DL, DSC) on the Stanford Sentiment Treebank datasets (SST-2 and SST-5), measured by accuracy."<SEP>"Table 9 presents experimental results on the effect of DL and DSC on sentiment classification tasks, specifically involving BERT fine-tuned with cross-entropy."",4
3,"BERT+DL",ORGANIZATION,"A model configuration combining BERT with Distillation Loss, achieving 94.37% accuracy on SST-2 and 54.63% on SST-5. This aligns with the use of DL (Distillation Loss) in BERT-based models as described in Table 9 for sentiment classification tasks.",20
4,"IMAGE_22","ORI_IMG",""The image is a table labeled 'Table 9: The effect of DL and DSC on sentiment classification tasks.' It presents experimental results comparing the performance of different training objectives when fine-tuning BERT on two versions of the Stanford Sentiment Treebank (SST) datasets: SST-2 and SST-5. The table has three columns: 'Model', 'SST-2 Acc', and 'SST-5 Acc'. The rows list three models: 'BERT+CE', 'BERT+DL', and 'BERT+DSC'. For SST-2, the accuracy values are as follows: BERT+CE achieves 94.90, BERT+DL achieves 94.37, and BERT+DSC achieves 94.84. For SST-5, the accuracy values are: BERT+CE achieves 55.57, BERT+DL achieves 54.63, and BERT+DSC achieves 55.19. The highest accuracy in both SST-2 and SST-5 is achieved by BERT+CE, with 94.90 and 55.57 respectively. The other two models (BERT+DL and BERT+DSC) show slightly lower performance, indicating that the proposed dice-based losses (DL and DSC) perform worse than the cross-entropy (CE) objective in accuracy-oriented tasks. This supports the claim in the context that dice loss is not accuracy-oriented and should be avoided for tasks where accuracy is the primary metric. The table uses bold formatting to emphasize the best-performing value in each column (94.90 and 55.57)."",7
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,""BERT (DEVLIN ET AL., 2018)"","BERT+DL","BERT+DL is an enhancement of BERT-Tagger with deep learning methods.",8.0,52
1,""BERT (DEVLIN ET AL., 2018)"","BERT+DSC","BERT+DSC is an enhancement of BERT-Tagger using dynamic state control.",8.0,52
2,"BERT+DSC","QUOREF","BERT+DSC improved upon BERT with EM of 62.44 and F1 of 67.52 on QuoRef.",9.0,41
3,"BERT+DL","QUOREF","BERT+DL improved upon BERT with EM of 62.03 and F1 of 66.88 on QuoRef.",7.0,41
4,""BERT (DEVLIN ET AL., 2018)"","TABLE 9",""BERT models with different loss functions (CE, DL, DSC) are evaluated in Table 9 on SST-2 and SST-5 for accuracy."",9.0,36
5,"BERT+DSC","SQUAD V1.1","BERT+DSC improved upon BERT with EM of 85.34 and F1 of 91.97 on SQuAD v1.1.",9.0,35
6,"BERT+DL","SQUAD V1.1","BERT+DL improved upon BERT with EM of 84.83 and F1 of 91.86 on SQuAD v1.1.",8.0,35
7,"BERT+DSC","CTB5","BERT+DSC is evaluated on the CTB5 dataset.",7.0,34
8,"BERT+DL","CTB5","BERT+DL is evaluated on the CTB5 dataset.",7.0,34
9,"BERT+DSC","IMAGE_19","BERT+DSC是从image_19中提取的实体。",10.0,33
10,"BERT+DL","IMAGE_19","BERT+DL是从image_19中提取的实体。",10.0,33
11,"BERT+DSC","IMAGE_20","BERT+DSC是从image_20中提取的实体。",10.0,33
12,"BERT+DL","IMAGE_20","BERT+DL是从image_20中提取的实体。",10.0,33
13,"BERT+DSC","IMAGE_16","BERT+DSC是从image_16中提取的实体。",10.0,33
14,"BERT+DL","IMAGE_16","BERT+DL是从image_16中提取的实体。",10.0,33
15,"BERT+DSC","SQUAD V2.0","BERT+DSC improved upon BERT with EM of 79.02 and F1 of 82.95 on SQuAD v2.0.",8.0,32
16,"BERT+DL","SQUAD V2.0","BERT+DL improved upon BERT with EM of 78.99 and F1 of 82.88 on SQuAD v2.0.",7.0,32
17,"BERT+DSC","UD1.4","BERT+DSC is evaluated on the UD1.4 dataset.",7.0,32
18,"BERT+DL","UD1.4","BERT+DL is evaluated on the UD1.4 dataset.",7.0,32
19,"BERT+DSC","IMAGE_21","BERT+DSC是从image_21中提取的实体。",10.0,30
20,"BERT+DL","IMAGE_21","BERT+DL是从image_21中提取的实体。",10.0,30
21,"BERT+DSC","CTB6","BERT+DSC is evaluated on the CTB6 dataset.",7.0,30
22,"BERT+DL","CTB6","BERT+DL is evaluated on the CTB6 dataset.",7.0,30
23,"BERT+CE","BERT+DSC",""BERT+DSC enhances BERT using a data selection or contrastive approach, achieving the highest score."",9.0,29
24,"BERT+CE","BERT+DL",""BERT+DL builds upon BERT by incorporating deep learning techniques, resulting in marginal gains."",7.0,29
25,"BERT+DSC","IMAGE_22","BERT+DSC是从image_22中提取的实体。",10.0,27
26,"BERT+DL","IMAGE_22","BERT+DL是从image_22中提取的实体。",10.0,27
27,"BERT+DSC","SST-2","BERT+DSC achieves an accuracy of 94.84% on the SST-2 dataset.",9.0,26
28,"BERT+DSC","SST-5","BERT+DSC achieves an accuracy of 55.19% on the SST-5 dataset.",9.0,26
29,"BERT+DL","SST-2","BERT+DL achieves an accuracy of 94.37% on the SST-2 dataset.",9.0,26
30,"BERT+DL","SST-5","BERT+DL achieves an accuracy of 54.63% on the SST-5 dataset.",9.0,26
31,"BERT+CE","BERT+FL",""BERT+FL is an extension of BERT with additional fine-tuning or learning strategy, improving performance slightly."",8.0,26
32,"BERT+DSC","Original Training Set (Original)","BERT+DSC outperforms the original BERT significantly.",9.0,25
33,"BERT+DL","Original Training Set (Original)","BERT+DL shows a small improvement over the original BERT.",6.0,25
34,"BERT+DSC","Combined Positive and Negative Augmentation (+ Positive & Negative)","BERT+DSC achieves the highest performance when both positive and negative samples are added.",10.0,24
35,"BERT+DSC","Positive Augmentation (+ Positive)","BERT+DSC improves further with positive samples.",8.0,24
36,"BERT+DL","Combined Positive and Negative Augmentation (+ Positive & Negative)","BERT+DL achieves peak performance with both sample types added.",8.0,24
37,"BERT+DL","Positive Augmentation (+ Positive)","BERT+DL improves with positive samples.",7.0,24
38,"BERT+DSC","Negative Downsampling (- Negative)","BERT+DSC still performs well even without negative samples.",7.0,24
39,"BERT+DSC","Negative Augmentation (+ Negative)","BERT+DSC shows moderate improvement with negative samples.",6.0,24
40,"BERT+DL","Negative Downsampling (- Negative)","BERT+DL performs better when negative samples are removed.",6.0,24
41,"BERT+DL","Negative Augmentation (+ Negative)","BERT+DL sees minimal gain from adding negative samples.",4.0,24
42,"BERT+CE","IMAGE_20","BERT是从image_20中提取的实体。",10.0,22
43,"BERT+CE","IMAGE_21","BERT是从image_21中提取的实体。",10.0,19
44,"BERT+CE","IMAGE_22","BERT+CE是从image_22中提取的实体。",10.0,16
45,"BERT+CE","SST-2","BERT+CE achieves an accuracy of 94.90% on the SST-2 dataset.",9.0,15
46,"BERT+CE","SST-5","BERT+CE achieves an accuracy of 55.57% on the SST-5 dataset.",9.0,15
47,"BERT+CE","Original Training Set (Original)","BERT is evaluated under the original condition as a baseline.",10.0,14
48,"IMAGE_22","SST-2","SST-2是从image_22中提取的实体。",10.0,13
49,"IMAGE_22","SST-5","SST-5是从image_22中提取的实体。",10.0,13
50,"IMAGE_22","TABLE 9","IMAGE_22" is the image of "TABLE 9".,10.0,11
51,"Accuracy (SST-2/SST-5)","IMAGE_22","Accuracy是从image_22中提取的实体。",10.0,10
52,"STANFORD SENTIMENT TREEBANK (SST)","TABLE 9",""Table 9 presents results from experiments on the Stanford Sentiment Treebank datasets, including SST-2 and SST-5."",10.0,7
53,"BERT + CE","TABLE 9",""Table 9 references 'BERT + CE' as a method involving fine-tuning BERT with cross-entropy, though 'BERT + CE' itself is not an entity type listed; thus, no explicit relationship is formed per allowed types."",0.0,5
    ```
    -----Sources-----
    ```csv
    id,content
0,"we used Spacy1 to retrieve entity mentions and replace them with new ones by linking mentions to their corresponding entities in DBpedia. The augmented set contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

• Negative augmentation ( $\cdot +$ negative) We created a more imbalanced dataset. The size of the newly constructed training set and the data augmented technique are exactly the same as +negative, except that we chose negative training examples as templates. The augmented training set contains 458,477 examples, with $21 \%$ being positive and $79 \%$ being negative.

Table 8: The effect of different data augmentation ways for QQP in terms of F1-score.   

<table><tr><td></td><td>original</td><td>+ positive</td><td> + negative</td><td> - negative</td><td>+ positive &amp; negative</td></tr><tr><td>BERT</td><td>91.3</td><td>92.27</td><td>90.08</td><td>89.73</td><td>93.14</td></tr><tr><td>BERT+FL</td><td>91.86(+0.56)</td><td>92.64(+0.37)</td><td>90.61(+0.53)</td><td>90.79(+1.06)</td><td>93.45(+0.31)</td></tr><tr><td>BERT+DL</td><td>91.92(+0.62)</td><td>92.87(+0.60)</td><td>90.22(+0.14)</td><td>90.49(+0.76)</td><td>93.52(+0.38)</td></tr><tr><td>BERT+DSC</td><td>92.11(+0.81)</td><td>92.92(+0.65)</td><td>90.78(+0.70)</td><td>90.80(+1.07)</td><td>93.63(+0.49)</td></tr></table>

# • Negative downsampling (- negative)

We down-sampled negative examples in the original training set to get a balanced training set. The down-sampled set contains 269,165 examples, with $50 \%$ being positive and $50 \%$ being negative.

# • Positive and negative augmentation $^ +$ positive $\pmb { \& }$ +negative)

We augmented the original training data with additional positive and negative examples with the data distribution staying the same. The augmented dataset contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

Results are shown in Table 8. We first look at the first line, with all results obtained using the MLE objective. We can see that $^ +$ positive outperforms original, and +negative underperforms original. This is in line with our expectation since $^ +$ positive creates a balanced dataset while +negative creates a more imbalanced dataset. Despite the fact that -negative creates a balanced dataset, the number of training data decreases, resulting in inferior performances.

DSC achieves the highest F1 score across all datasets. Specially, for $^ +$ positive, DSC achieves minor improvements $\left( + 0 . 0 5 \mathrm { F 1 } \right.$ ) over DL. In contrast, it significantly outperforms DL for $^ +$ negative dataset. This is in line with our expectation since DSC helps more on more imbalanced datasets. The performance of FL and DL are not consistent across different datasets, while DSC consistently performs the best on all datasets.

# 5.2 Dice loss for accuracy-oriented tasks?

We argue that the cross-entropy objective is actually accuracy-oriented, whereas the proposed losses perform as a soft version of F1 score. To explore the effect of the dice loss on accuracyoriented tasks such as text classification, we conduct experiments on the Stanford Sentiment Treebank (SST) datasets including SST-2 and SST-5. We fine-tuned $\mathrm { B E R T _ { L a r g e } }$ with different training objectives. Experimental results for SST are shown in Table 9. For SST-5, BERT with CE achieves 55.57 in terms of accuracy, while DL and DSC perform slightly worse (54.63 and 55.19, respectively). Similar phenomenon is observed for SST-2. These results verify that the proposed dice loss is not accuracy-oriented, and should not be used for accuracy-oriented tasks.

<table><tr><td></td><td>SST-2</td><td>SST-5</td></tr><tr><td>Model</td><td>Acc</td><td>Acc</td></tr><tr><td>BERT+CE</td><td>94.90</td><td>55.57</td></tr><tr><td>BERT+DL</td><td>94.37</td><td>54.63</td></tr><tr><td>BERT+DSC</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling"
1,"</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling the tradeoff between false-negatives and false-positives. In this subsection, we explore the effect of hyperparameters (i.e., $\alpha$ and $\beta$ ) in TI to test how they manipulate the tradeoff. We conduct experiments on the Chinese OntoNotes4.0 NER dataset and English QuoRef MRC dataset. Experimental results are shown in Table 10. The highest F1 on Chinese OntoNotes4.0 is 84.67 when $\alpha$ is set to 0.6 while for QuoRef, the highest F1 is 68.44 when $\alpha$ is set to 0.4. In addition, we can observe that the performance varies a lot as $\alpha$ changes in distinct datasets, which shows that the hyperparameters $\alpha , \beta$ acturally play an important role in TI.

# 6 Conclusion

In this paper, we propose the dice-based loss to narrow down the gap between training objective and evaluation metrics (F1 score). Experimental results show that the proposed loss function help

<table><tr><td>α</td><td>Chinese Onto4.0</td><td>English QuoRef</td></tr><tr><td>α=0.1</td><td>80.13</td><td>63.23</td></tr><tr><td>α=0.2</td><td>81.17</td><td>63.45</td></tr><tr><td>α= 0.3</td><td>84.22</td><td>65.88</td></tr><tr><td>α=0.4</td><td>84.52</td><td>68.44</td></tr><tr><td>α=0.5</td><td>84.47</td><td>67.52</td></tr><tr><td>α=0.6</td><td>84.67</td><td>66.35</td></tr><tr><td>α=0.7</td><td>81.81</td><td>65.09</td></tr><tr><td>α=0.8</td><td>80.97</td><td>64.13</td></tr><tr><td>α= 0.9</td><td>80.21</td><td>64.84</td></tr></table>

Table 10: The effect of hyperparameters in Tversky Index. We set $\beta = 1 - \alpha$ and thus we only list $\alpha$ here.

to achieve significant performance boost without changing model architectures.

# Acknowledgement

We thank all anonymous reviewers, as well as Qinghong Han, Wei Wu and Jiawei Wu for their comments and suggestions. The work is supported by the National Natural Science Foundation of China (NSFC No. 61625107 and 61751209).

# References

Bernd Bohnet, Ryan T. McDonald, Gonc¸alo Simoes, ˜ Daniel Andor, Emily Pitler, and Joshua Maynez. 2018. Morphosyntactic tagging with a meta-bilstm model over context sensitive token encodings. In Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics, ACL 2018, Melbourne, Australia, July 15-20, 2018, Volume 1: Long Papers, pages 2642–2652.

Haw-Shiuan Chang, Erik G. Learned-Miller, and Andrew McCallum. 2017. Active bias: Training more accurate neural networks by emphasizing high variance samples. In NIPS.

N. V. Chawla, K. W. Bowyer, Lawrence O. Hall, and W. P. Kegelmeyer. 2002. Smote: Synthetic minority over-sampling technique. J. Artif. Intell. Res., 16:321– 357.

Danqi Chen, Adam Fisch, Jason Weston, and Antoine Bordes. 2017. Reading wikipedia to answer opendomain questions. arXiv preprint arXiv:1704.00051.

Kean Chen, Jianguo Li, Weiyao Lin, John See, Ji Wang, Lingyu Duan, Zhibo Chen, Changwei He, and Junni Zou. 2019. Towards accurate one-stage object detection with ap-loss. In IEEE Conference on Computer Vision and Pattern Recognition, CVPR 2019, Long Beach, CA, USA, June 16-20, 2019, pages 5119–5127.

Shijuan Chen, Haibo He, and Edwardo A. Garcia. 2010. Ramoboost: Ranked minority oversampling in boosting. IEEE Transactions on Neural Networks, 21:1624– 1642.

Kevin Clark, Minh-Thang Luong, Christopher D. Manning, and Quoc V. Le. 2018. Semi-supervised sequence modeling with cross-view training. In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Procfessing, Brussels, Belgium, October 31 - November 4, 2018, pages 191"
    ```
    

### Initial LLM Response

### Performance Comparison: BERT+DL vs. BERT+DSC on SST-5

According to **Table 9**, which evaluates different BERT-based models on the **Stanford Sentiment Treebank (SST)** datasets using **accuracy** as the metric:

- **BERT+DL** achieves an accuracy of **54.63%** on **SST-5**.
- **BERT+DSC** achieves an accuracy of **55.19%** on **SST-5**.

### Interpretation

- **BERT+DSC outperforms BERT+DL** on SST-5 by **0.56 percentage points** (55.19 – 54.63 = 0.56).
- However, **both models underperform compared to BERT+CE** (Cross-Entropy), which achieves **55.57%** accuracy—the highest among the three.
- This aligns with the paper's observation that **dice-based losses (DL and DSC)** are designed to optimize **F1-score-like objectives**, not accuracy. Hence, they perform slightly worse than CE on **accuracy-oriented tasks** like SST sentiment classification.

### Summary

> On SST-5, **BERT+DSC (55.19%) performs better than BERT+DL (54.63%)**, but both are marginally inferior to the standard **BERT+CE (55.57%)** baseline in terms of accuracy.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_22.jpg
**Response**: ### Table Analysis

The provided table (Table 9) presents the performance of three BERT-based models—BERT+CE, BERT+DL, and BERT+DSC—on two versions of the Stanford Sentiment Treebank (SST) datasets: SST-2 and SST-5. The metric used is accuracy (Acc).

For **SST-5**, the accuracy values are as follows:
- **BERT+DL**: 54.63%
- **BERT+DSC**: 55.19%

This indicates that **BERT+DSC outperforms BERT+DL** on the SST-5 dataset by a margin of **0.56 percentage points**.

### Image Analysis

The image labeled "IMAGE_22" contains the same table (Table 9) described above. It explicitly shows the accuracy scores for each model on both SST-2 and SST-5. The visual presentation confirms the numerical data from the table, with **bold formatting highlighting the highest accuracy in each column**. In the SST-5 column, **BERT+CE** has the highest accuracy (55.57%), followed by **BERT+DSC** (55.19%) and then **BERT+DL** (54.63%). This visual emphasis reinforces the ranking of performance across models.

### Integrated Insights

Based on the combined analysis of the table and image:
- **BERT+DSC achieves higher accuracy than BERT+DL on SST-5**, with scores of 55.19% versus 54.63%, respectively.
- While both models use dice-based losses (DL and DSC), **DSC performs better than DL** in this accuracy-oriented task.
- The source text further supports this observation, stating that “the proposed dice loss is not accuracy-oriented,” and that **DSC performs slightly better than DL** on SST-5, though both fall short of BERT+CE.

Thus, **BERT+DSC outperforms BERT+DL on SST-5**, demonstrating a modest but consistent advantage in accuracy.

### Merged Multimodal Response

BERT+DSC outperforms BERT+DL on the SST-5 dataset. Specifically, BERT+DSC achieves an accuracy of **55.19%**, while BERT+DL achieves **54.63%**, giving BERT+DSC a **0.56 percentage point advantage**. Although both models use dice-based loss functions, DSC (Dice Similarity Coefficient) demonstrates slightly better performance than DL (Dice Loss) in this accuracy-oriented evaluation. Notably, neither model surpasses BERT+CE, which attains the highest accuracy on SST-5 at **55.57%**.

### Final Response

On the SST-5 dataset, **BERT+DSC outperforms BERT+DL** in terms of accuracy:

- **BERT+DL** achieves an accuracy of **54.63%**  
- **BERT+DSC** achieves an accuracy of **55.19%**

This represents a **0.56 percentage point improvement** for BERT+DSC over BERT+DL. However, both models are slightly outperformed by **BERT+CE**, which reaches **55.57%** accuracy—the highest among the three. The relatively lower performance of dice-based losses (DL and DSC) compared to cross-entropy (CE) is consistent with their design objective: optimizing F1-score-like metrics rather than accuracy.

---

## Query: By how much does the accuracy of BERT+CE on SST-2 exceed that of BERT+DL?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"BERT+DSC",ORGANIZATION,"A model configuration combining BERT with Deep Supervision Classification, achieving 94.84% accuracy on SST-2 and 55.19% on SST-5. This matches the application of DSC (a proposed loss function or training objective) with BERT in experiments, including those reported in Table 9.",20
1,"BERT+CE",ORGANIZATION,"A model configuration combining BERT with Cross-Entropy loss, achieving 94.90% accuracy on SST-2 and 55.57% on SST-5. This corresponds to the BERT model fine-tuned with cross-entropy as referenced in Table 9 for sentiment classification tasks.",9
2,"IMAGE_22","ORI_IMG",""The image is a table labeled 'Table 9: The effect of DL and DSC on sentiment classification tasks.' It presents experimental results comparing the performance of different training objectives when fine-tuning BERT on two versions of the Stanford Sentiment Treebank (SST) datasets: SST-2 and SST-5. The table has three columns: 'Model', 'SST-2 Acc', and 'SST-5 Acc'. The rows list three models: 'BERT+CE', 'BERT+DL', and 'BERT+DSC'. For SST-2, the accuracy values are as follows: BERT+CE achieves 94.90, BERT+DL achieves 94.37, and BERT+DSC achieves 94.84. For SST-5, the accuracy values are: BERT+CE achieves 55.57, BERT+DL achieves 54.63, and BERT+DSC achieves 55.19. The highest accuracy in both SST-2 and SST-5 is achieved by BERT+CE, with 94.90 and 55.57 respectively. The other two models (BERT+DL and BERT+DSC) show slightly lower performance, indicating that the proposed dice-based losses (DL and DSC) perform worse than the cross-entropy (CE) objective in accuracy-oriented tasks. This supports the claim in the context that dice loss is not accuracy-oriented and should be avoided for tasks where accuracy is the primary metric. The table uses bold formatting to emphasize the best-performing value in each column (94.90 and 55.57)."",7
3,"BERT+DL",ORGANIZATION,"A model configuration combining BERT with Distillation Loss, achieving 94.37% accuracy on SST-2 and 54.63% on SST-5. This aligns with the use of DL (Distillation Loss) in BERT-based models as described in Table 9 for sentiment classification tasks.",20
4,"TABLE 9","EVENT",""Table 9 displays the performance of BERT models with different loss functions (CE, DL, DSC) on the Stanford Sentiment Treebank datasets (SST-2 and SST-5), measured by accuracy."<SEP>"Table 9 presents experimental results on the effect of DL and DSC on sentiment classification tasks, specifically involving BERT fine-tuned with cross-entropy."",4
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,""BERT (DEVLIN ET AL., 2018)"","BERT+DL","BERT+DL is an enhancement of BERT-Tagger with deep learning methods.",8.0,52
1,""BERT (DEVLIN ET AL., 2018)"","BERT+DSC","BERT+DSC is an enhancement of BERT-Tagger using dynamic state control.",8.0,52
2,"BERT+DSC","QUOREF","BERT+DSC improved upon BERT with EM of 62.44 and F1 of 67.52 on QuoRef.",9.0,41
3,"BERT+DL","QUOREF","BERT+DL improved upon BERT with EM of 62.03 and F1 of 66.88 on QuoRef.",7.0,41
4,""BERT (DEVLIN ET AL., 2018)"","TABLE 9",""BERT models with different loss functions (CE, DL, DSC) are evaluated in Table 9 on SST-2 and SST-5 for accuracy."",9.0,36
5,"BERT+DSC","SQUAD V1.1","BERT+DSC improved upon BERT with EM of 85.34 and F1 of 91.97 on SQuAD v1.1.",9.0,35
6,"BERT+DL","SQUAD V1.1","BERT+DL improved upon BERT with EM of 84.83 and F1 of 91.86 on SQuAD v1.1.",8.0,35
7,"BERT+DSC","CTB5","BERT+DSC is evaluated on the CTB5 dataset.",7.0,34
8,"BERT+DL","CTB5","BERT+DL is evaluated on the CTB5 dataset.",7.0,34
9,"BERT+DSC","IMAGE_19","BERT+DSC是从image_19中提取的实体。",10.0,33
10,"BERT+DL","IMAGE_19","BERT+DL是从image_19中提取的实体。",10.0,33
11,"BERT+DSC","IMAGE_20","BERT+DSC是从image_20中提取的实体。",10.0,33
12,"BERT+DL","IMAGE_20","BERT+DL是从image_20中提取的实体。",10.0,33
13,"BERT+DSC","IMAGE_16","BERT+DSC是从image_16中提取的实体。",10.0,33
14,"BERT+DL","IMAGE_16","BERT+DL是从image_16中提取的实体。",10.0,33
15,"BERT+DSC","SQUAD V2.0","BERT+DSC improved upon BERT with EM of 79.02 and F1 of 82.95 on SQuAD v2.0.",8.0,32
16,"BERT+DL","SQUAD V2.0","BERT+DL improved upon BERT with EM of 78.99 and F1 of 82.88 on SQuAD v2.0.",7.0,32
17,"BERT+DSC","UD1.4","BERT+DSC is evaluated on the UD1.4 dataset.",7.0,32
18,"BERT+DL","UD1.4","BERT+DL is evaluated on the UD1.4 dataset.",7.0,32
19,"BERT+DSC","IMAGE_21","BERT+DSC是从image_21中提取的实体。",10.0,30
20,"BERT+DL","IMAGE_21","BERT+DL是从image_21中提取的实体。",10.0,30
21,"BERT+DSC","CTB6","BERT+DSC is evaluated on the CTB6 dataset.",7.0,30
22,"BERT+DL","CTB6","BERT+DL is evaluated on the CTB6 dataset.",7.0,30
23,"BERT+CE","BERT+DSC",""BERT+DSC enhances BERT using a data selection or contrastive approach, achieving the highest score."",9.0,29
24,"BERT+CE","BERT+DL",""BERT+DL builds upon BERT by incorporating deep learning techniques, resulting in marginal gains."",7.0,29
25,"BERT+DSC","IMAGE_22","BERT+DSC是从image_22中提取的实体。",10.0,27
26,"BERT+DL","IMAGE_22","BERT+DL是从image_22中提取的实体。",10.0,27
27,"BERT+DSC","SST-2","BERT+DSC achieves an accuracy of 94.84% on the SST-2 dataset.",9.0,26
28,"BERT+DSC","SST-5","BERT+DSC achieves an accuracy of 55.19% on the SST-5 dataset.",9.0,26
29,"BERT+DL","SST-2","BERT+DL achieves an accuracy of 94.37% on the SST-2 dataset.",9.0,26
30,"BERT+DL","SST-5","BERT+DL achieves an accuracy of 54.63% on the SST-5 dataset.",9.0,26
31,"BERT+CE","BERT+FL",""BERT+FL is an extension of BERT with additional fine-tuning or learning strategy, improving performance slightly."",8.0,26
32,"BERT+DSC","Original Training Set (Original)","BERT+DSC outperforms the original BERT significantly.",9.0,25
33,"BERT+DL","Original Training Set (Original)","BERT+DL shows a small improvement over the original BERT.",6.0,25
34,"BERT+DSC","Combined Positive and Negative Augmentation (+ Positive & Negative)","BERT+DSC achieves the highest performance when both positive and negative samples are added.",10.0,24
35,"BERT+DSC","Positive Augmentation (+ Positive)","BERT+DSC improves further with positive samples.",8.0,24
36,"BERT+DL","Combined Positive and Negative Augmentation (+ Positive & Negative)","BERT+DL achieves peak performance with both sample types added.",8.0,24
37,"BERT+DL","Positive Augmentation (+ Positive)","BERT+DL improves with positive samples.",7.0,24
38,"BERT+DSC","Negative Downsampling (- Negative)","BERT+DSC still performs well even without negative samples.",7.0,24
39,"BERT+DSC","Negative Augmentation (+ Negative)","BERT+DSC shows moderate improvement with negative samples.",6.0,24
40,"BERT+DL","Negative Downsampling (- Negative)","BERT+DL performs better when negative samples are removed.",6.0,24
41,"BERT+DL","Negative Augmentation (+ Negative)","BERT+DL sees minimal gain from adding negative samples.",4.0,24
42,"BERT+CE","IMAGE_20","BERT是从image_20中提取的实体。",10.0,22
43,"BERT+CE","IMAGE_21","BERT是从image_21中提取的实体。",10.0,19
44,"BERT+CE","IMAGE_22","BERT+CE是从image_22中提取的实体。",10.0,16
45,"BERT+CE","SST-2","BERT+CE achieves an accuracy of 94.90% on the SST-2 dataset.",9.0,15
46,"BERT+CE","SST-5","BERT+CE achieves an accuracy of 55.57% on the SST-5 dataset.",9.0,15
47,"BERT+CE","Original Training Set (Original)","BERT is evaluated under the original condition as a baseline.",10.0,14
48,"IMAGE_22","SST-2","SST-2是从image_22中提取的实体。",10.0,13
49,"IMAGE_22","SST-5","SST-5是从image_22中提取的实体。",10.0,13
50,"IMAGE_22","TABLE 9","IMAGE_22" is the image of "TABLE 9".,10.0,11
51,"Accuracy (SST-2/SST-5)","IMAGE_22","Accuracy是从image_22中提取的实体。",10.0,10
52,"STANFORD SENTIMENT TREEBANK (SST)","TABLE 9",""Table 9 presents results from experiments on the Stanford Sentiment Treebank datasets, including SST-2 and SST-5."",10.0,7
53,"BERT + CE","TABLE 9",""Table 9 references 'BERT + CE' as a method involving fine-tuning BERT with cross-entropy, though 'BERT + CE' itself is not an entity type listed; thus, no explicit relationship is formed per allowed types."",0.0,5
    ```
    -----Sources-----
    ```csv
    id,content
0,"we used Spacy1 to retrieve entity mentions and replace them with new ones by linking mentions to their corresponding entities in DBpedia. The augmented set contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

• Negative augmentation ( $\cdot +$ negative) We created a more imbalanced dataset. The size of the newly constructed training set and the data augmented technique are exactly the same as +negative, except that we chose negative training examples as templates. The augmented training set contains 458,477 examples, with $21 \%$ being positive and $79 \%$ being negative.

Table 8: The effect of different data augmentation ways for QQP in terms of F1-score.   

<table><tr><td></td><td>original</td><td>+ positive</td><td> + negative</td><td> - negative</td><td>+ positive &amp; negative</td></tr><tr><td>BERT</td><td>91.3</td><td>92.27</td><td>90.08</td><td>89.73</td><td>93.14</td></tr><tr><td>BERT+FL</td><td>91.86(+0.56)</td><td>92.64(+0.37)</td><td>90.61(+0.53)</td><td>90.79(+1.06)</td><td>93.45(+0.31)</td></tr><tr><td>BERT+DL</td><td>91.92(+0.62)</td><td>92.87(+0.60)</td><td>90.22(+0.14)</td><td>90.49(+0.76)</td><td>93.52(+0.38)</td></tr><tr><td>BERT+DSC</td><td>92.11(+0.81)</td><td>92.92(+0.65)</td><td>90.78(+0.70)</td><td>90.80(+1.07)</td><td>93.63(+0.49)</td></tr></table>

# • Negative downsampling (- negative)

We down-sampled negative examples in the original training set to get a balanced training set. The down-sampled set contains 269,165 examples, with $50 \%$ being positive and $50 \%$ being negative.

# • Positive and negative augmentation $^ +$ positive $\pmb { \& }$ +negative)

We augmented the original training data with additional positive and negative examples with the data distribution staying the same. The augmented dataset contains 458,477 examples, with $50 \%$ being positive and $50 \%$ being negative.

Results are shown in Table 8. We first look at the first line, with all results obtained using the MLE objective. We can see that $^ +$ positive outperforms original, and +negative underperforms original. This is in line with our expectation since $^ +$ positive creates a balanced dataset while +negative creates a more imbalanced dataset. Despite the fact that -negative creates a balanced dataset, the number of training data decreases, resulting in inferior performances.

DSC achieves the highest F1 score across all datasets. Specially, for $^ +$ positive, DSC achieves minor improvements $\left( + 0 . 0 5 \mathrm { F 1 } \right.$ ) over DL. In contrast, it significantly outperforms DL for $^ +$ negative dataset. This is in line with our expectation since DSC helps more on more imbalanced datasets. The performance of FL and DL are not consistent across different datasets, while DSC consistently performs the best on all datasets.

# 5.2 Dice loss for accuracy-oriented tasks?

We argue that the cross-entropy objective is actually accuracy-oriented, whereas the proposed losses perform as a soft version of F1 score. To explore the effect of the dice loss on accuracyoriented tasks such as text classification, we conduct experiments on the Stanford Sentiment Treebank (SST) datasets including SST-2 and SST-5. We fine-tuned $\mathrm { B E R T _ { L a r g e } }$ with different training objectives. Experimental results for SST are shown in Table 9. For SST-5, BERT with CE achieves 55.57 in terms of accuracy, while DL and DSC perform slightly worse (54.63 and 55.19, respectively). Similar phenomenon is observed for SST-2. These results verify that the proposed dice loss is not accuracy-oriented, and should not be used for accuracy-oriented tasks.

<table><tr><td></td><td>SST-2</td><td>SST-5</td></tr><tr><td>Model</td><td>Acc</td><td>Acc</td></tr><tr><td>BERT+CE</td><td>94.90</td><td>55.57</td></tr><tr><td>BERT+DL</td><td>94.37</td><td>54.63</td></tr><tr><td>BERT+DSC</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling"
1,"</td><td>94.84</td><td>55.19</td></tr></table>

Table 9: The effect of DL and DSC on sentiment classification tasks. BERT $\mathrm { + C E }$ refers to fine-tuning BERT and setting cross-entropy as the training objective.

# 5.3 Hyper-parameters in Tversky Index

As mentioned in Section 3.3, Tversky index (TI) offers the flexibility in controlling the tradeoff between false-negatives and false-positives. In this subsection, we explore the effect of hyperparameters (i.e., $\alpha$ and $\beta$ ) in TI to test how they manipulate the tradeoff. We conduct experiments on the Chinese OntoNotes4.0 NER dataset and English QuoRef MRC dataset. Experimental results are shown in Table 10. The highest F1 on Chinese OntoNotes4.0 is 84.67 when $\alpha$ is set to 0.6 while for QuoRef, the highest F1 is 68.44 when $\alpha$ is set to 0.4. In addition, we can observe that the performance varies a lot as $\alpha$ changes in distinct datasets, which shows that the hyperparameters $\alpha , \beta$ acturally play an important role in TI.

# 6 Conclusion

In this paper, we propose the dice-based loss to narrow down the gap between training objective and evaluation metrics (F1 score). Experimental results show that the proposed loss function help

<table><tr><td>α</td><td>Chinese Onto4.0</td><td>English QuoRef</td></tr><tr><td>α=0.1</td><td>80.13</td><td>63.23</td></tr><tr><td>α=0.2</td><td>81.17</td><td>63.45</td></tr><tr><td>α= 0.3</td><td>84.22</td><td>65.88</td></tr><tr><td>α=0.4</td><td>84.52</td><td>68.44</td></tr><tr><td>α=0.5</td><td>84.47</td><td>67.52</td></tr><tr><td>α=0.6</td><td>84.67</td><td>66.35</td></tr><tr><td>α=0.7</td><td>81.81</td><td>65.09</td></tr><tr><td>α=0.8</td><td>80.97</td><td>64.13</td></tr><tr><td>α= 0.9</td><td>80.21</td><td>64.84</td></tr></table>

Table 10: The effect of hyperparameters in Tversky Index. We set $\beta = 1 - \alpha$ and thus we only list $\alpha$ here.

to achieve significant performance boost without changing model architectures.

# Acknowledgement

We thank all anonymous reviewers, as well as Qinghong Han, Wei Wu and Jiawei Wu for their comments and suggestions. The work is supported by the National Natural Science Foundation of China (NSFC No. 61625107 and 61751209).

# References

Bernd Bohnet, Ryan T. McDonald, Gonc¸alo Simoes, ˜ Daniel Andor, Emily Pitler, and Joshua Maynez. 2018. Morphosyntactic tagging with a meta-bilstm model over context sensitive token encodings. In Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics, ACL 2018, Melbourne, Australia, July 15-20, 2018, Volume 1: Long Papers, pages 2642–2652.

Haw-Shiuan Chang, Erik G. Learned-Miller, and Andrew McCallum. 2017. Active bias: Training more accurate neural networks by emphasizing high variance samples. In NIPS.

N. V. Chawla, K. W. Bowyer, Lawrence O. Hall, and W. P. Kegelmeyer. 2002. Smote: Synthetic minority over-sampling technique. J. Artif. Intell. Res., 16:321– 357.

Danqi Chen, Adam Fisch, Jason Weston, and Antoine Bordes. 2017. Reading wikipedia to answer opendomain questions. arXiv preprint arXiv:1704.00051.

Kean Chen, Jianguo Li, Weiyao Lin, John See, Ji Wang, Lingyu Duan, Zhibo Chen, Changwei He, and Junni Zou. 2019. Towards accurate one-stage object detection with ap-loss. In IEEE Conference on Computer Vision and Pattern Recognition, CVPR 2019, Long Beach, CA, USA, June 16-20, 2019, pages 5119–5127.

Shijuan Chen, Haibo He, and Edwardo A. Garcia. 2010. Ramoboost: Ranked minority oversampling in boosting. IEEE Transactions on Neural Networks, 21:1624– 1642.

Kevin Clark, Minh-Thang Luong, Christopher D. Manning, and Quoc V. Le. 2018. Semi-supervised sequence modeling with cross-view training. In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Procfessing, Brussels, Belgium, October 31 - November 4, 2018, pages 191"
    ```
    

### Initial LLM Response

The accuracy of **BERT+CE** on **SST-2** is **94.90%**, while that of **BERT+DL** is **94.37%**.

To compute the difference:

$$
94.90 - 94.37 = 0.53
$$

Thus, **BERT+CE outperforms BERT+DL by 0.53 percentage points** in accuracy on the SST-2 dataset.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_22.jpg
**Response**: ### Table Analysis

The provided table (Table 9) presents the accuracy of three BERT-based models—BERT+CE, BERT+DL, and BERT+DSC—on two versions of the Stanford Sentiment Treebank (SST) datasets: SST-2 and SST-5. The relevant data for the query is in the **SST-2 Acc** column:

- **BERT+CE** achieves an accuracy of **94.90%**.
- **BERT+DL** achieves an accuracy of **94.37%**.

To calculate how much the accuracy of BERT+CE exceeds that of BERT+DL on SST-2:

$$
94.90 - 94.37 = 0.53
$$

Thus, BERT+CE outperforms BERT+DL by **0.53 percentage points** on SST-2.

### Image Analysis

The image (IMAGE_22) corresponds directly to Table 9, as confirmed by the relationship:
- `"IMAGE_22" → "TABLE 9"` with a weight of 10.0, indicating a strong association.

The image contains the same tabular data as described above, including bold formatting to emphasize the highest accuracy values (94.90 and 55.57), which aligns with the description in the entities. This visual confirmation supports the accuracy values used in the calculation.

### Integrated Insights

The difference in performance between BERT+CE and BERT+DL on SST-2 is consistent across both the textual description and the visual representation in IMAGE_22. The result highlights that cross-entropy (CE) loss leads to slightly higher accuracy than distillation loss (DL) in this task, supporting the conclusion that CE is more effective for accuracy-oriented tasks like sentiment classification.

### Final Answer

The accuracy of BERT+CE on SST-2 exceeds that of BERT+DL by **0.53 percentage points**.

### Merged Multimodal Response

The accuracy of BERT+CE on SST-2 exceeds that of BERT+DL by **0.53 percentage points**.

- BERT+CE accuracy on SST-2: **94.90%**  
- BERT+DL accuracy on SST-2: **94.37%**  
- Difference: **94.90 − 94.37 = 0.53**

### Final Response

The accuracy of BERT+CE on SST-2 exceeds that of BERT+DL by **0.53 percentage points**.

- BERT+CE accuracy: **94.90%**  
- BERT+DL accuracy: **94.37%**  
- Difference: **94.90 − 94.37 = 0.53**

---

## Query: What is the ratio of negative to positive examples for the Quoref task?

### Context


    -----Entities-----
    ```csv
    id,entity,type,description,rank
0,"IMAGE_1","ORI_IMG",""The image is a table labeled 'Table 1: Number of positive and negative examples and their ratios for different data-imbalanced NLP tasks.' The table presents statistical information about the number of negative (# neg), positive (# pos) examples, and their respective ratios for various natural language processing (NLP) tasks. It consists of five rows and four columns. The first column lists the tasks: CoNLL03 NER, OntoNotes5.0 NER, SQuAD 1.1 (Rajpurkar et al., 2016), SQuAD 2.0 (Rajpurkar et al., 2018), and QUOREF (Dasigi et al., 2019). The second column shows the number of negative examples: 170K for CoNLL03 NER, 1.96M for OntoNotes5.0 NER, 10.3M for SQuAD 1.1, 15.4M for SQuAD 2.0, and 6.52M for QUOREF. The third column displays the number of positive examples: 34K for CoNLL03 NER, 239K for OntoNotes5.0 NER, 175K for SQuAD 1.1, 188K for SQuAD 2.0, and 38.6K for QUOREF. The fourth column provides the ratio of negative to positive examples: 4.98 for CoNLL03 NER, 8.18 for OntoNotes5.0 NER, 55.9 for SQuAD 1.1, 82.0 for SQuAD 2.0, and 169 for QUOREF. The table highlights the increasing severity of data imbalance across these tasks, particularly in machine reading comprehension (MRC) tasks like SQuAD and QUOREF, where the ratio exceeds 50 and reaches as high as 169. This extreme imbalance reflects the nature of MRC tasks, where only a few tokens are labeled as positive (e.g., start or end of an answer span), while the vast majority are background (negative). The context emphasizes that such imbalance poses challenges in training models and motivates the use of specialized loss functions like Dice loss to improve performance."",10
1,"RATIO","EVENT","Column header in Table 1 indicating the ratio of negative to positive instances in each NLP dataset, highlighting the severity of data imbalance. Ratios range from approximately 5 in CoNLL03 NER to as high as 169 in QUOREF, underscoring the challenge of training models that perform well on minority (positive) classes.",6
2,"TABLE 1","EVENT","Table 1 presents statistics on the number of positive and negative examples and their ratios across various data-imbalanced NLP tasks discussed in the paper.",6
3,"Negative Downsampling (- Negative)","EVENT","The '- Negative' condition involves downsampling negative examples from the original dataset to achieve class balance (50% positive, 50% negative), reducing the total training size to 269,165 examples. Despite achieving balance, the reduced data volume leads to lower performance—e.g., BERT’s F1 falls to 89.73—indicating that data quantity remains critical even when class distribution is balanced.",4
4,"Negative Augmentation (+ Negative)","EVENT","The '+ Negative' condition creates a more imbalanced dataset by augmenting negative examples using the same entity replacement technique applied to negative templates, resulting in a training set with 21% positive and 79% negative samples. This exacerbates class imbalance and typically degrades performance—e.g., BERT’s F1 on QQP drops to 90.08—highlighting the adverse effects of increasing negative sample dominance without rebalancing.",4
    ```
    -----Relationships-----
    ```csv
    id,source,target,description,weight,rank
0,"IMAGE_1","QUOREF",""QUOREF (Dasigi et al., 2019)是从image_1中提取的实体。"",10.0,31
1,"QUOREF","TABLE 1","Table 1 reports the extreme imbalance ratio (169) for the QUOREF dataset.",8.0,27
2,"QUOREF","RATIO","The ratio of negative to positive instances for QUOREF is 169 as indicated in the 'ratio' column.",8.0,27
3,"BERT+DSC","Negative Downsampling (- Negative)","BERT+DSC still performs well even without negative samples.",7.0,24
4,"BERT+DSC","Negative Augmentation (+ Negative)","BERT+DSC shows moderate improvement with negative samples.",6.0,24
5,"BERT+DL","Negative Downsampling (- Negative)","BERT+DL performs better when negative samples are removed.",6.0,24
6,"BERT+DL","Negative Augmentation (+ Negative)","BERT+DL sees minimal gain from adding negative samples.",4.0,24
7,"BERT+FL","Negative Downsampling (- Negative)","BERT+FL benefits slightly from removing negative samples.",6.0,21
8,"BERT+FL","Negative Augmentation (+ Negative)","BERT+FL performs worse than original when negative samples are added.",5.0,21
9,"IMAGE_1","ONTONOTES5.0","OntoNotes5.0 NER是从image_1中提取的实体。",10.0,19
10,"IMAGE_1","SQUAD 2.0",""SQuAD 2.0 (Rajpurkar et al., 2018)是从image_1中提取的实体。"",10.0,17
11,"CONLL03","IMAGE_1","CoNLL03 NER是从image_1中提取的实体。",10.0,17
12,"IMAGE_1","SQUAD 1.1",""SQuAD 1.1 (Rajpurkar et al., 2016)是从image_1中提取的实体。"",10.0,17
13,"# POS","IMAGE_1","# pos是从image_1中提取的实体。",10.0,16
14,"IMAGE_1","TABLE 1","IMAGE_1" is the image of "TABLE 1".,10.0,16
15,"IMAGE_1","TASK","Task是从image_1中提取的实体。",10.0,16
16,"# NEG","IMAGE_1","# neg是从image_1中提取的实体。",10.0,16
17,"IMAGE_1","RATIO","ratio是从image_1中提取的实体。",10.0,16
18,"ONTONOTES5.0","RATIO","The ratio of negative to positive instances for OntoNotes5.0 NER is 8.18 as indicated in the 'ratio' column.",8.0,15
19,"ONTONOTES5.0","TABLE 1","Table 1 provides statistics on the data imbalance in the OntoNotes5.0 dataset.",8.0,15
20,"IMAGE_21","Negative Augmentation (+ Negative)","+ negative是从image_21中提取的实体。",10.0,14
21,"IMAGE_21","Negative Downsampling (- Negative)","- negative是从image_21中提取的实体。",10.0,14
22,"RATIO","SQUAD 1.1","The ratio of negative to positive instances for SQuAD 1.1 is 55.9 as indicated in the 'ratio' column.",8.0,13
23,"CONLL03","RATIO","The ratio of negative to positive instances for CoNLL03 NER is 4.98 as indicated in the 'ratio' column.",8.0,13
24,"RATIO","SQUAD 2.0","The ratio of negative to positive instances for SQuAD 2.0 is 82.0 as indicated in the 'ratio' column.",8.0,13
25,"SQUAD 1.1","TABLE 1","Table 1 lists the number of negative and positive examples and the ratio for SQuAD 1.1.",8.0,13
26,"CONLL03","TABLE 1",""Table 1 includes quantitative data about the CoNLL03 dataset, specifically its negative-positive example ratio."",8.0,13
27,"SQUAD 2.0","TABLE 1","Table 1 includes data imbalance metrics for the SQuAD 2.0 dataset.",8.0,13
    ```
    -----Sources-----
    ```csv
    id,content
0,"# Dice Loss for Data-imbalanced NLP Tasks

Xiaoya $\mathbf { L i } ^ { * }$ , Xiaofei $\mathbf { S u n } ^ { \ast }$ , Yuxian Meng♣, Junjun Liang♣, Fei $\mathbf { W } \mathbf { u } ^ { \bullet }$ and Jiwei $\mathbf { L i } ^ { \mathbf { \alpha } \mathbf { \hat { \alpha } } \mathbf { \hat { \alpha } } }$

♠ Department of Computer Science and Technology, Zhejiang University ♣ Shannon.AI {xiaoya li, xiaofei sun, yuxian meng, jiwei li}@shannonai.com, wufei $@$ cs.zju.edu.cn

# Abstract

Many NLP tasks such as tagging and machine reading comprehension (MRC) are faced with the severe data imbalance issue: negative examples significantly outnumber positive ones, and the huge number of easy-negative examples overwhelms training. The most commonly used cross entropy criteria is actually accuracy-oriented, which creates a discrepancy between training and test. At training time, each training instance contributes equally to the objective function, while at test time F1 score concerns more about positive examples.

In this paper, we propose to use dice loss in replacement of the standard cross-entropy objective for data-imbalanced NLP tasks. Dice loss is based on the Sørensen–Dice coefficient (Sorensen, 1948) or Tversky index (Tversky, 1977), which attaches similar importance to false positives and false negatives, and is more immune to the data-imbalance issue. To further alleviate the dominating influence from easy-negative examples in training, we propose to associate training examples with dynamically adjusted weights to deemphasize easy-negative examples. Experimental results show that this strategy narrows down the gap between the F1 score in evaluation and the dice loss in training.

With the proposed training objective, we observe significant performance boosts over a wide range of data imbalanced NLP tasks. Notably, we are able to achieve SOTA results on CTB5, CTB6 and UD1.4 for the part of speech tagging task, and competitive or even better results on CoNLL03, OntoNotes5.0, MSRA and OntoNotes4.0 for the named entity recognition task along with the machine reading comprehension and paraphrase identification tasks. The code can be found at https://github.com/ShannonAI/ dice_loss_for_NLP.

Table 1: Number of positive and negative examples and their ratios for different data-imbalanced NLP tasks.   

<table><tr><td rowspan=1 colspan=1>Task</td><td rowspan=1 colspan=1>#neg</td><td rowspan=1 colspan=1>#pos</td><td rowspan=1 colspan=1>ratio</td></tr><tr><td rowspan=1 colspan=1>CoNLL03NER</td><td rowspan=1 colspan=1>170K</td><td rowspan=1 colspan=1>34K</td><td rowspan=1 colspan=1>4.98</td></tr><tr><td rowspan=1 colspan=1>OntoNotes5.0 NER</td><td rowspan=1 colspan=1>1.96M</td><td rowspan=1 colspan=1>239K</td><td rowspan=1 colspan=1>8.18</td></tr><tr><td rowspan=1 colspan=1>SQuAD 1.1 (Rajpurkar et al., 2016)</td><td rowspan=1 colspan=1>10.3M</td><td rowspan=1 colspan=1>175K</td><td rowspan=1 colspan=1>55.9</td></tr><tr><td rowspan=1 colspan=1>SQuAD 2.0 (Rajpurkar et al., 2018)</td><td rowspan=1 colspan=1>15.4M</td><td rowspan=1 colspan=1>188K</td><td rowspan=1 colspan=1>82.0</td></tr><tr><td rowspan=1 colspan=1>QUOREF(Dasigi et al., 2019)</td><td rowspan=1 colspan=1>6.52M</td><td rowspan=1 colspan=1>38.6K</td><td rowspan=1 colspan=1>169</td></tr></table>

# 1 Introduction

Data imbalance is a common issue in a variety of NLP tasks such as tagging and machine reading comprehension. Table 1 gives concrete examples: for the Named Entity Recognition (NER) task (Sang and De Meulder, 2003; Nadeau and Sekine, 2007), most tokens are backgrounds with tagging class $O$ . Specifically, the number of tokens with tagging class $O$ is 5 times as many as those with entity labels for the CoNLL03 dataset and 8 times for the OntoNotes5.0 dataset; Dataimbalanced issue is more severe for MRC tasks (Rajpurkar et al., 2016; Nguyen et al., 2016; Rajpurkar et al., 2018; Kocisk ˇ y et al. \` , 2018; Dasigi et al., 2019) with the value of negative-positive ratio being 50-200, which is due to the reason that the task of MRC is usually formalized as predicting the starting and ending indexes conditioned on the query and the context, and given a chunk of text of an arbitrary length, only two tokens are positive (or of interest) with all the rest being background.

Data imbalance results in the following"
    ```
    

### Initial LLM Response

The ratio of negative to positive examples for the **QUOREF** task is **169**.

This figure is explicitly reported in **Table 1** of the provided source material, which summarizes data imbalance statistics across several NLP tasks. For QUOREF (Dasigi et al., 2019), the table lists:
- **6.52 million** negative examples,
- **38.6 thousand** positive examples,
- yielding a **negative-to-positive ratio of 169**.

This extremely high ratio underscores the severe class imbalance inherent in machine reading comprehension (MRC) tasks like QUOREF, where only a tiny fraction of tokens correspond to answer spans (positive examples), and the vast majority are non-answer (negative) tokens.

### Multimodal Processing (1 images)

**Image**: examples/example_working/images/image_1.jpg
**Response**: ### Table Analysis

The provided table, labeled as "Table 1: Number of positive and negative examples and their ratios for different data-imbalanced NLP tasks," contains detailed statistics for various natural language processing (NLP) tasks. The relevant row for the **QUOREF** task is:

- **Task**: QUOREF (Dasigi et al., 2019)
- **# neg**: 6.52M
- **# pos**: 38.6K
- **ratio**: **169**

This ratio indicates that for every positive example in the QUOREF dataset, there are approximately 169 negative examples, highlighting an extreme level of class imbalance.

### Image Analysis

The image referenced (`IMAGE_1`) is a visual representation of the same table described above. It explicitly displays the **ratio column**, where the value **169** is listed under the QUOREF task. This confirms the numerical data extracted from the table and reinforces the severity of data imbalance in this task.

### Integrated Insights

The ratio of negative to positive examples for the **QUOREF** task is **169**, as directly reported in both the tabular data and the associated image. This high ratio reflects the nature of machine reading comprehension (MRC) tasks, where only a small number of tokens (e.g., start/end of answer spans) are labeled as positive, while the vast majority are background (negative). Such extreme imbalance poses significant challenges for model training, particularly when using standard loss functions like cross-entropy, which may prioritize accuracy over precision and recall on minority classes.

Thus, the answer to the query is:
> The ratio of negative to positive examples for the QUOREF task is **169**.

### Merged Multimodal Response

The ratio of negative to positive examples for the QUOREF task is **169**. This means that for every positive example in the dataset, there are approximately 169 negative examples, reflecting a significant class imbalance typical of machine reading comprehension tasks.

### Final Response

The ratio of negative to positive examples for the QUOREF task is **169**. This means that for every positive example in the dataset, there are approximately 169 negative examples.

This figure is explicitly reported in **Table 1** of the source material, which provides data imbalance statistics across several NLP tasks. Specifically, for QUOREF (Dasigi et al., 2019), the dataset contains:
- **6.52 million** negative examples,
- **38.6 thousand** positive examples,

which yields a **negative-to-positive ratio of 169**. This extreme imbalance is typical in machine reading comprehension tasks, where only a small fraction of tokens correspond to answer spans (positive examples), and the vast majority are non-answer (negative) tokens.