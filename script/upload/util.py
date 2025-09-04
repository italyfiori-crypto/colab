from typing import List

def unique_list(list: List[str]) -> List[str]:
    unique_list = []
    unique_set = set()
    
    for item in list:
        if item in unique_set:
            continue
        
        unique_set.add(item)
        unique_list.append(item)

    return unique_list

