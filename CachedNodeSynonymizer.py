import os
import pickle
from typing import Union, List, Dict


class CachedNodeSynonymizer:
    def __init__(self, base_synonymizer, cache_path: str = "data/synonymizer_cache.pkl"):
        """
        Wraps a NodeSynonymizer instance to cache results and minimize network requests.

        :param base_synonymizer: The initialized NodeSynonymizer object.
        :param cache_path: Path to load/save the cache to disk.
        """
        self.synonymizer = base_synonymizer
        self.cache_path = cache_path
        self._cache = {}

        self.load_cache()

    def get_canonical_curies(self, curies: Union[str, List[str]] = None, names: Union[str, List[str]] = None) -> Dict:
        """
        Drop-in replacement for synonymizer.get_canonical_curies.
        """
        results = {}
        to_fetch_curies = []
        to_fetch_names = []

        # 1. Check cache for CURIEs
        if curies:
            curies_list = [curies] if isinstance(curies, str) else curies
            for c in curies_list:
                cache_key = f"curie:{c}"
                if cache_key in self._cache:
                    results[c] = self._cache[cache_key]
                else:
                    to_fetch_curies.append(c)

        # 2. Check cache for Names
        if names:
            names_list = [names] if isinstance(names, str) else names
            for n in names_list:
                cache_key = f"name:{n}"
                if cache_key in self._cache:
                    results[n] = self._cache[cache_key]
                else:
                    to_fetch_names.append(n)

        # 3. Fetch missing CURIEs from the network
        if to_fetch_curies:
            new_curie_results = self.synonymizer.get_canonical_curies(curies=to_fetch_curies)
            if new_curie_results:
                for c, res in new_curie_results.items():
                    self._cache[f"curie:{c}"] = res
                    results[c] = res

        # 4. Fetch missing Names from the network
        if to_fetch_names:
            new_name_results = self.synonymizer.get_canonical_curies(names=to_fetch_names)
            if new_name_results:
                for n, res in new_name_results.items():
                    self._cache[f"name:{n}"] = res
                    results[n] = res

        return results

    def save_cache(self):
        """Saves the current in-memory cache to disk."""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, 'wb') as f:
            pickle.dump(self._cache, f)
        print(f"Synonymizer cache saved to {self.cache_path} ({len(self._cache)} entries)")

    def load_cache(self):
        """Loads the cache from disk if it exists."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'rb') as f:
                    self._cache = pickle.load(f)
                print(f"Loaded synonymizer cache from {self.cache_path} ({len(self._cache)} entries)")
            except Exception as e:
                print(f"Warning: Failed to load cache from {self.cache_path}: {e}")
                self._cache = {}
        else:
            self._cache = {}