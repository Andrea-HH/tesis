"""Genera edición pública10 desde la instantánea privada, sin Git ni microdatos."""
from tesis_enasem.quality_outputs import export_public
if __name__=='__main__':
    print(export_public())
