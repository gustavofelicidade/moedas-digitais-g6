import pandas as pd
import numpy as np

def extract_wallet_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores comportamentais determinísticos por carteira a partir do dataset do Ethereum.
    
    Colunas Necessárias de Entrada (first_order_df.csv):
        - TxHash (str): Hash único da transação.
        - TimeStamp (int/datetime): Momento em que a transação ocorreu (Unix timestamp em segundos ou datetime).
        - From (str): Endereço do remetente (carteira de origem).
        - To (str): Endereço do destinatário.
        - Value (float): Volume transferido em ETH (denominador: ETH).
        - isError (int/bool): Indicador binário de falha (0 = Sucesso, 1 = Falha/Erro).

    Limitações:
        - Janela temporal dependente do recorte histórico contido no dataset original.
        - Mede apenas transações de primeira ordem (first-order transfers); interações complexas em camada interna de contratos inteligentes não estão visíveis nesta tabela base.
        - Os resultados devem ser interpretados exclusivamente como sinais comportamentais e métricas de atividade, não constituindo prova direta de fraude ou uso malicioso de automação.
    """
    df_clean = df.copy()
    
    # Normaliza timestamp
    if not pd.api.types.is_datetime64_any_dtype(df_clean['TimeStamp']):
        df_clean['TimeStamp'] = pd.to_datetime(df_clean['TimeStamp'], unit='s', errors='coerce')
        
    df_clean = df_clean.sort_values(by=['From', 'TimeStamp'])
    
    # 1. Agrupamentos principais por carteira
    features = df_clean.groupby('From').agg(
        total_transactions=('TxHash', 'count'),
        total_value_sent=('Value', 'sum'),
        avg_value_sent=('Value', 'mean'),
        max_value_sent=('Value', 'max'),
        min_value_sent=('Value', 'min'),
        std_value_sent=('Value', lambda x: x.std() if len(x) > 1 else 0.0),
        unique_destinations=('To', 'nunique'),
        error_count=('isError', lambda x: (x == 1).sum()),
        error_rate=('isError', lambda x: (x == 1).mean())
    ).reset_index()
    
    # 2. Cálculo dos intervalos entre transações (delta time)
    df_clean['prev_timestamp'] = df_clean.groupby('From')['TimeStamp'].shift(1)
    df_clean['time_diff_seconds'] = (df_clean['TimeStamp'] - df_clean['prev_timestamp']).dt.total_seconds()
    
    time_metrics = df_clean.groupby('From').agg(
        avg_inter_tx_time_seconds=('time_diff_seconds', 'mean'),
        min_inter_tx_time_seconds=('time_diff_seconds', 'min')
    ).reset_index()
    
    time_metrics['avg_inter_tx_time_seconds'] = time_metrics['avg_inter_tx_time_seconds'].fillna(0.0)
    time_metrics['min_inter_tx_time_seconds'] = time_metrics['min_inter_tx_time_seconds'].fillna(0.0)
    
    # Merge com os dados de tempo
    features = pd.merge(features, time_metrics, on='From', how='left')
    
    return features
