using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using System.IO;
using BayatGames.SaveGameFree;
using TMPro;

public class WordCard : CardTypeBase
{
    [SerializeField] public string wordSelected;
    
    string[] wordListVerbs = new string[8] { "appear", "vanish", "contract", "expand", "fail", "succeed", "help", "hinder" };
    string[] wordListAdjectives = new string[8] { "empty", "full", "messy", "neat", "boring", "fun", "young", "old" };
    string[] wordListPrepositions = new string[8] { "before", "after", "in", "out", "against", "for", "below", "above"};
    string[] wordListNouns = new string[8] { "despair", "hope", "past", "present", "poverty", "wealth", "success", "failure"};
    string[] wordListSynVerbs = new string[8] { "choose", "select", "refuse", "reject", "collect", "gather", "forbid", "ban" };
    string[] wordListSynAdjectives = new string[8] { "little", "tiny", "bad", "awful", "pretty", "handsome"  ,"mad", "crazy"};
    string[] wordListGrammar = new string[8] { "I", "am", "you", "are", "she", "is", "either", "or" };
    string[] wordListQuestions = new string[8] { "where", "here", "when", "now", "why", "because", "who", "she" };
    
    // 7 word pairs. It was too hard of a task.
    // string[] wordListVerbs = new string[14] { "appear", "vanish", "contract", "expand",
    //     "fail", "succeed", "help", "hinder", "separate", "join",
    //     "build", "destroy", "conceal", "reveal" };
    // string[] wordListAdjectives = new string[14] { "empty", "full", "messy", "neat",
    //     "boring", "fun", "young", "old", "private", "public",
    //     "quiet", "loud", "sweet", "sour" };
    // string[] wordListPrepositions = new string[14] { "before", "after", "away from", "towards",
    //     "in", "out", "against", "for", "below", "above",
    //     "backward", "forward", "here", "there" };
    // string[] wordListNouns = new string[14] { "despair", "hope", "past", "present",
    //     "poverty", "wealth", "success", "failure", "virtue", "vice",
    //     "war", "peace", "bless", "curse" };
    // string[] wordListSynVerbs = new string[14] { "choose", "select", "close", "shut", "refuse", "reject",
    //     "collect", "gather", "defend", "protect" , "forbid", "ban" ,"begin", "start"};
    // string[] wordListSynAdjectives = new string[14] { "happy", "amused", "little", "tiny", "good", "terrific",
    //     "bad", "awful", "pretty", "handsome" , "angry", "annoyed" ,"mad", "crazy"};
    // string[] wordListGrammar = new string[14] { "I", "am", "you", "are", "she", "is",
    //     "to", "be", "either", "or" , "neither", "nor" ,"not only", "but also"};
    // string[] wordListQuestions = new string[14] { "what", "this", "where", "here", "when", "now",
    //     "why", "because", "who", "she" , "whom", "her" ,"how often", "rarely"};
    
    string[] characterList = new string[19] { "e", "t", "a", "o", "u", "i", "n", "s", "r", "h", "l", "d", "c" , "d", "p", "m", "g", "f", "b"};

    string[] wordList;
    public List<string> wordSelectedList = new List<string>();
    LevelController levelController;

    TextMeshProUGUI textRenderer;
    string wordInitial;
    string nihilWord = "nihil";
    int randomIndex;
    string modeWord = "verbs";

    protected override void Start()
    {
        base.Start();
        levelController = LevelController.Instance;
        SetWordsForMode();
        randomIndex = Random.Range(0, wordList.Length);
        wordInitial = SetWord();
    }

    public void SetWordsForMode()
    {
        if(modeWord == "verbs")
        {
            wordList = wordListVerbs;
        }
        else if(modeWord == "adjectives")
        {
            wordList = wordListAdjectives;
        }
        else if (modeWord == "prepositions")
        {
            wordList = wordListPrepositions;
        }
        else if (modeWord == "nouns")
        {
            wordList = wordListNouns;
        }
        else if (modeWord == "synVerbs")
        {
            wordList = wordListSynVerbs;
        }
        else if (modeWord == "synAdjectives")
        {
            wordList = wordListSynAdjectives;
            textRenderer.fontSize = 15f;
        }
        else if (modeWord == "grammar")
        {
            wordList = wordListGrammar;
        }
        else if (modeWord == "questions")
        {
            wordList = wordListQuestions;
        }
        else if (modeWord == "scrabble")
        {
            wordList = characterList;
        }
    }

    public string SetWord()
    {
        //wordSelected = "    ";
        textRenderer = GetComponentInChildren<TextMeshProUGUI>();
        if (activated)
        {
            wordSelected = wordList[randomIndex];
            // Guard: remove any stale empty-string entries that can appear
            // due to WebGL frame-timing during card initialization.
            wordSelectedList.RemoveAll(s => string.IsNullOrEmpty(s));
            if (!wordSelectedList.Contains(wordSelected))
            {
                wordSelectedList.Add(wordSelected);
            }
        }

        if (cardSuper)
        {
            wordSelected = nihilWord;
            wordSelectedList = new List<string>();
            wordSelectedList.Add(nihilWord);
        }

        SetWordCard(wordSelected);

        return wordSelected;
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
    }


    public float ComputeMergeWordGain(List<string> newWordList)
    {
        return ComputeMergeWordGain(newWordList, out _);
    }

    // Same tier-bucketing as the single-arg overload, but also reports the
    // raw multiplier the merge would apply (product of 0.9 / 2.0 / 2.5 ops
    // in the verbs/nouns path, or the single 1.5 / 2.0 / 2.5 value in the
    // scrabble path). Used by AgentBridge so the LLM preview can show the
    // actual multiplier instead of the tier's "canonical" one — compound
    // pair matches can push the real multiplier above 2.5 (e.g. 4.0 from
    // two pair matches), and the tier-3 label "×2.5" was understating
    // these cases to the agent.
    public float ComputeMergeWordGain(List<string> newWordList, out float multiplier)
    {
        multiplier = 1f;
        if (modeWord != "scrabble")
        {
            if (newWordList.Count == 0 && wordSelectedList.Count == 0)
            {
                return 0f;
            }

            if (newWordList.Count == 1 && wordSelectedList.Count == 1 &&
                   newWordList[0] == nihilWord && wordSelectedList[0] == nihilWord)
            {
                multiplier = manaIncreaseMultiplier3;
                return 3f;
            }

            if (wordSelectedList.Count == 1 && wordSelectedList[0] == nihilWord &&
                newWordList.Contains(nihilWord) == false)
            {
                multiplier = manaReductionMultiplier;
                return -1f;
            }

            if (wordSelectedList.Contains(nihilWord) == false &&
                newWordList.Count == 1 && newWordList[0] == nihilWord)
            {
                return 0f;
            }

            float multiplierWord = 1f;
            foreach (string newWord in newWordList)
            {
                bool identicalWord = false;
                foreach (string wordSelectedIter1 in wordSelectedList)
                {
                    //Debug.Log("The word collection item before: " + wordSelectedIter1);
                    if (wordSelectedIter1 == newWord)
                    {
                        multiplierWord = multiplierWord * manaReductionMultiplier;
                        identicalWord = true;
                        break;
                    }
                }

                if (identicalWord)
                {
                    continue;
                }

                bool matchingWords = false;
                int loopIndexOuter = 0;
                string wordIter;
                foreach (string wordSelectedIter in wordSelectedList)
                {
                    for (int loopIndex = 0; loopIndex < wordList.Length - 1; loopIndex += 2)
                    {
                        wordIter = wordList[loopIndex];
                        //Debug.Log("The word iter at: " + wordIter);
                        if (wordSelectedIter == wordIter && newWord == wordList[loopIndex + 1] ||
                            wordSelectedIter == wordList[loopIndex + 1] && newWord == wordIter)
                        {
                            multiplierWord = multiplierWord * manaIncreaseMultiplier2;
                            matchingWords = true;
                            break;
                        }
                    }
                    if (matchingWords)
                    {
                        break;
                    }
                    loopIndexOuter += 1;
                }

            }

            multiplier = multiplierWord;

            if (multiplierWord >= manaIncreaseMultiplier3)
            {
                return 3f;
            }
            else if (multiplierWord >= manaIncreaseMultiplier2 && multiplierWord < manaIncreaseMultiplier3)
            {
                return 2f;
            }
            else if (multiplierWord > 1 && multiplierWord < manaIncreaseMultiplier2)
            {
                return 1f;
            }
            else if (multiplierWord < 1)
            {
                return -1f;
            }
        }
        else
        {
            if (newWordList.Count == 0 && wordSelectedList.Count == 0)
            {
                return 0f;
            }

            string newWord = newWordList[0] + wordSelectedList[0];
            //Debug.Log(newWord);
            bool keyExists = levelController.DictionaryWordLookup(newWord);
            if (keyExists)
            {
                if (newWord.Length < 3 && newWord.Length > 1)
                {
                    multiplier = manaIncreaseMultiplier1;
                    return 1f;
                }
                else if (newWord.Length >= 3 && newWord.Length < 4)
                {
                    multiplier = manaIncreaseMultiplier2;
                    return 2f;
                }
                else if (newWord.Length >= 4)
                {
                    multiplier = manaIncreaseMultiplier3;
                    return 3f;
                }
            }
            else
            {
                return 0f;
            }
        }

        return 0f;
    }

    public void MergeWordCard(List<string> newWordList)
    {
        if(modeWord != "scrabble")
        {
            if (newWordList.Count == 0 && wordSelectedList.Count == 0)
            {
                return;
            }

            if (newWordList.Count == 1 && wordSelectedList.Count == 1 &&
                   newWordList[0] == nihilWord && wordSelectedList[0] == nihilWord)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                SetStringFromList();
                return;
            }

            if (wordSelectedList.Count == 1 && wordSelectedList[0] == nihilWord &&
                newWordList.Contains(nihilWord) == false)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetStringFromList();
                return;
            }

            if (wordSelectedList.Contains(nihilWord) == false &&
                newWordList.Count == 1 && newWordList[0] == nihilWord)
            {
                wordSelectedList = newWordList;
                SetStringFromList();
                return;
            }

            bool wordRemoved = false;
            foreach (string newWord in newWordList)
            {
                bool identicalWord = false;
                foreach (string wordSelectedIter1 in wordSelectedList)
                {
                    //Debug.Log("The word collection item before: " + wordSelectedIter1);
                    if (wordSelectedIter1 == newWord)
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                        identicalWord = true;
                        break;
                    }
                }

                if (identicalWord)
                {
                    continue;
                }

                bool matchingWords = false;
                int indexMatchWord = 0;
                int loopIndexOuter = 0;
                string wordIter;
                foreach (string wordSelectedIter in wordSelectedList)
                {
                    for (int loopIndex = 0; loopIndex < wordList.Length - 1; loopIndex += 2)
                    {
                        wordIter = wordList[loopIndex];
                        //Debug.Log("The word iter at: " + wordIter);
                        if (wordSelectedIter == wordIter && newWord == wordList[loopIndex + 1] ||
                            wordSelectedIter == wordList[loopIndex + 1] && newWord == wordIter)
                        {
                            cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                            matchingWords = true;
                            //wordSelectedList.FindIndex(x => x.StartsWith(wordSelectedIter));
                            indexMatchWord = loopIndexOuter;

                            break;
                        }
                    }
                    if (matchingWords)
                    {
                        break;
                    }
                    loopIndexOuter += 1;
                }

                if (matchingWords)
                {
                    wordSelectedList.RemoveAt(indexMatchWord);
                    wordRemoved = true;
                }
                else
                {
                    if (!wordSelectedList.Contains(newWord) && wordSelectedList.Count < 2)
                    {
                        wordSelectedList.Add(newWord);
                    }
                }

            }

            // After removing matched words, promote to nihil if the list
            // is empty or contains only empty-string ghosts left over from
            // a WebGL initialisation race.
            wordSelectedList.RemoveAll(s => string.IsNullOrEmpty(s));
            if (wordRemoved && wordSelectedList.Count == 0)
            {
                wordSelectedList.Add(nihilWord);
            }

        }
        else //scrabble logic
        {
            if (newWordList.Count == 0 && wordSelectedList.Count == 0)
            {
                return;
            }

            wordSelectedList[0] = newWordList[0] + wordSelectedList[0];
            bool keyExists = levelController.DictionaryWordLookup(wordSelectedList[0]);
            if (keyExists)
            {
                if (wordSelectedList[0].Length < 3 && wordSelectedList[0].Length > 1)
                {
                    cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                }
                else if (wordSelectedList[0].Length >= 3 && wordSelectedList[0].Length < 4)
                {
                    cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                }
                else if (wordSelectedList[0].Length >= 4)
                {
                    cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                }
            }

        }

        SetStringFromList();

    }

    private void SetStringFromList()
    {
        string stringShow = null;
        foreach (string wordSelectedIter2 in wordSelectedList)
        {
            if (wordSelectedIter2 == "    ")
            {
                continue;
            }
            //Debug.Log("The word collection item after: " + wordSelectedIter2);
            if (stringShow == null)
            {
                stringShow = wordSelectedIter2;
            }
            else
            {
                stringShow += System.Environment.NewLine + wordSelectedIter2;
            }

        }
        SetWordCard(stringShow);
    }

    public void SetWordCard(string stringCard)
    {
        if(activated)
        {
            textRenderer.text = stringCard;
        }
        else
        {
            textRenderer.text = "    ";
        }
                
    }

    public void SetModeWord(string modeWordSet)
    {
        modeWord = modeWordSet;
        SetWordsForMode();
    }

    public string GetModeShape()
    {
        return modeWord;
    }

}
