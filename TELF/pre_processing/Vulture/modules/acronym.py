import re
import spacy
import warnings

from TELF.pre_processing.Vulture.modules import VultureModuleBase
from TELF.pre_processing.Vulture.tokens_analysis.top_words import get_top_words

FIRST_LETTER = 0
LAST_PART_INDEX = -1

def transform_acronyms_to_substitutions(old_list):
    """
    TODO: Document this
    """
    new_list = []
    for dictionary in old_list:
        if dictionary:  
            index_dictionary = {}
            for key, value in dictionary.items():
                new_key = '_'.join(key.split())

                index_dictionary[key] = new_key
                index_dictionary[value] = new_key

            new_list.append(index_dictionary)
        else:
            new_list.append({})
                
    return new_list


def flatten_acronym_dict(acronym_dict):
    """
    Transform the acronym operator data into the format that will work for consolidation and substitution operators.

    Parameters
    ----------
    acronym_dict: dict
        The output from AcronymDetector

    Returns
    -------
    list
        a list of dict that contain the acronyms.
    """
    acronym_dict_list = []
    for id, data in acronym_dict.items():
        acronym_dict_list.append(data['Acronyms'])
      
    return acronym_dict_list

class AcronymDetector(VultureModuleBase):
    """
    An operator that detects Acronyms in text.
    """

    def __init__(self, 
                 gram_range=list(range(2,8)), 
                 replace_raw=False, 
                 join_with='_', 
                 frozen=None):
        
        super().__init__(frozen)
        self.module_type = "OPERATOR"
        self.gram_range = gram_range
        self.current_document_id = None
        self.replace_raw = replace_raw
        self.join_with = join_with

        
    def __call__(self, document):
        return self.run(document)
        
    def run(self, document):
        """
        Run the acronym detection

        Parameters
        ----------
        document: tuple
            A document id, document text pair for which to perform acronym detection

        Returns
        -------
        tuple
            Tuple of document id and operation result
        """
        doc_id, doc_text = document
        self.current_document_id = doc_id
        doc_operation_result = self._detect_acronym(doc_text)
        return (doc_id, doc_operation_result)
    

    def  _detect_acronym(self, text):
        """
        Detect acronyms in a given string

        Parametersfrozen
        ----------
        text: str
            A string to etect acronyms over

        Returns
        -------
        str
            Dictionary of entity name and correcponding set of entities
        """
        only_acronyms = {}
        for n in self.gram_range:
            cur_n_grams =  get_top_words(   [text], 
                                            top_n=99999, 
                                            n_gram=n+1, 
                                            verbose=False, 
                                            filename=None
                                        ) 
            only_acronyms.update(  self._detect_acronym_helper(cur_n_grams) )

        replaced_text = ''
        if self.replace_raw:
            """
            Assumes if the acronym is defined in the text, it will not occur as the full text without the acronym
            example: If the acronym is 'EP' and the text is 'example part', this 'example part' will not occur by itself.
                    Properly defined acronyms will have the text once, then the acronym througout the rest of the document.
            """
            replaced_text = text
            for  full_form, acronym in only_acronyms.items():

                acronym_search = re.escape(acronym)
                acronym_src_joined = re.escape(full_form.replace(" ", self.join_with))
                acronym_src = re.escape(full_form)
                # replaces full strings with nothing, then corrects double spaces introduced by this -- ex: "The Example Part EP" becomes "The EP"
                replaced_text = re.sub(r'\b{}\b'.format(acronym_src), '', replaced_text)
                # replaces acronyms with comma joined full form -- ex: "The EP" becomes "The Example_Part"
                # print(f'prereplace = {replaced_text}')
                replaced_text = re.sub(r'\b{}\b'.format(acronym_search), acronym_src_joined, replaced_text)
                # print(f'postreplace = {replaced_text}')
                
        return {"Acronyms":only_acronyms, "replaced_text":replaced_text}
    

    def _detect_acronym_helper(self, df):
        """
        Detect acronyms based on the input DataFrame.

        Parameters
        ----------
        self: object
            The AcronymDetector object
        df: DataFrame
            A DataFrame containing 'word', 'tf', and 'df' columns

        Returns
        -------
        dict
            A dictionary containing detected acronyms
        """
        acronyms = {}
        for gram,tf, df in zip(df['word'],df['tf'], df['df']):
            gram_parts = gram.split()
            gram_without_end = gram_parts[:LAST_PART_INDEX]        
            gram_without_end_acronym = "".join([gram_part[FIRST_LETTER] for gram_part in gram_without_end])
            last_part = gram_parts[LAST_PART_INDEX]

            gram_without_beginning = gram_parts[1:]        
            first_part = gram_parts[0]
            gram_without_beginning_acronym = "".join([gram_part[FIRST_LETTER] for gram_part in gram_without_beginning])

            first_is_acronym = gram_without_beginning_acronym == first_part
            last_is_acronym = gram_without_end_acronym == last_part

            if first_is_acronym or last_is_acronym:
                if last_is_acronym:
                    words_composing_acronym = " ".join(gram_without_end)
                    acronym = last_part
                else:
                    words_composing_acronym = " ".join(gram_without_beginning)      
                    acronym = first_part

                if words_composing_acronym in acronyms:
                    warning_sring = f'The document at id="{self.current_document_id}" defines "{last_part}" as an acronym twice, using last occurance!'

                    warnings.warn(warning_sring)
                acronyms[words_composing_acronym] = acronym

        return acronyms
