
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from keras.layers import Input, Embedding, Flatten, concatenate, Lambda, Dense
from keras.regularizers import l2
from keras import backend as K
from keras.models import Model

from shibaer.util import load_pickle_files, read_metadata, ICD9_columns, drug_columns, preprocess_data
from shibaer.features import add_death_columns

EMBEDDING_REGULARIZATION = .0

meta_data = read_metadata()


def visit2vec(numeric_data_size, categocial_columns, categorical_families, targets):
    """
    Build a visit2vec model -- representation of a single visit

    :param numeric_data_size: int

    :param categocial_columns: list
        (name, n_cats)

    :param categorical_families: list
        [{"name":"ICD-9", "n-items": 67, "emb-size":10, "n-cols":3}, ...

    :param targets: list
        (target_name, target_size)

    :return:
    """

    # All numeric data goes here
    numeric_data = Input(shape=(numeric_data_size,))

    # Simple categorical columns are 1-hot
    simple_categorical_inputs = []
    for col_name, n_cats in categocial_columns:
        print("Building col: ", col_name)
        this_input = Input(shape=(n_cats,), name="input_" + col_name)
        simple_categorical_inputs.append(this_input)

    # Embeddings for categorical families
    fam_categorical_inputs = []
    fam_categoricals = []
    for c_fam in categorical_families:
        print("Building family: ", c_fam["name"])
        this_emb = Embedding(c_fam["n-items"], c_fam["emb-size"], name="embedding_" + c_fam["name"], embeddings_regularizer=l2(EMBEDDING_REGULARIZATION))
        for i in range(c_fam["n-cols"]):
            this_input = Input(shape=(1,), name="input_" + c_fam["name"] + "_" + str(i))
            this_out = Lambda(lambda inp: K.mean(inp, axis=1))(this_emb(this_input))

            fam_categorical_inputs.append(this_input)
            fam_categoricals.append(this_out)

    user_vector = concatenate([numeric_data] + simple_categorical_inputs + fam_categoricals, name="user_vector")

    outputs = []
    for target_name, target_size in targets:
        print("Building otuput: ", target_name)
        this_out = Dense(target_size, name="target_"+target_name)(user_vector)
        outputs.append(this_out)

    model = Model(inputs=[numeric_data]+simple_categorical_inputs+fam_categorical_inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=["accuracy"])
    model.summary()
    return model


def train(data):
    # Numeric data
    numeric_cols = meta_data.loc[meta_data.data_type == 'numeric'].index
    numeric_cols = [c for c in numeric_cols.values if c in data.columns]
    numeric_data_size = len(numeric_cols)

    #
    categocial_columns = [
        ("gender", 3),
    ]

    # Get lists of ICD-9 codes and drugs
    ICD9_list = np.unique([l for icd9_list in data[ICD9_columns].values.flatten() for l in icd9_list])
    drug_list = np.unique([l for drug_list in pd.Series(data[drug_columns].values.flatten()).dropna().values
                           for l in drug_list])

    #
    categorical_families = [
        {"name": "ICD-9", "n-items": ICD9_list.shape[0], "emb-size": 10, "n-cols": len(ICD9_columns)},
        {"name": "drugs", "n-items": drug_list.shape[0], "emb-size": 10, "n-cols": len(drug_columns)}
    ]
    categorical_families = []

    targets = [("T_mortality2d", 2)]

    model = visit2vec(numeric_data_size, categocial_columns, categorical_families, targets)

    # --- Generate training data ---

    numeric_inputs = data[numeric_cols].fillna(0).values
    numeric_inputs = StandardScaler().fit_transform(numeric_inputs)

    cat_inputs = [pd.get_dummies(data[col].astype('category')).values for col, _ in categocial_columns]

    icd_9_encoder = LabelEncoder().fit(ICD9_list)
    drug_encoder = LabelEncoder().fit(drug_list)
    for col in ICD9_columns:
        data[col] = data[col].fillna(0).apply(lambda v: icd_9_encoder.transform(v) if v != 0 and len(v) > 0 else v)
    for col in drug_columns:
        data[col] = data[col].fillna(0).apply(lambda v: drug_encoder.transform(v) if v != 0 and len(v) > 0 else v)

    fam_inputs = [data[col].values for col in ICD9_columns] + [data[col] for col in drug_columns]

    inputs = [numeric_inputs] + cat_inputs + fam_inputs
    inputs = [numeric_inputs] + cat_inputs

    outputs = [np.eye(t_size)[data[t_name].astype(int).values.flatten()] for t_name, t_size in targets]
    for t_name, t_size in targets:
        print("Target: ")
        print(data[t_name].value_counts())

    model.fit(inputs,
              outputs,
              epochs=100,
              verbose=2,
              validation_split=.2)

    return model


if __name__ == "__main__":

    data = load_pickle_files("DATAM", "ER", is_small=False)
    data = add_death_columns(data)
    data = preprocess_data(data)

    train(data)

