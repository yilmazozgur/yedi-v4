using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class NumberCard : CardTypeBase
{
    [SerializeField] public float numberSelected;
    [SerializeField] float maxValueAdd = 3f;
    [SerializeField] float maxValueMultiply = 4f;
    float[] gcdList = { 2f, 3f, 4f, 5f, 7f, 8f, 9f, 10f, 14f, 15f, 18f, 21f};
    string[] vectorList = { "(0,0)", "(0,1)", "(1,0)", "(1,1)", "(0,-1)", "(-1,0)", "(-1,-1)", "(1,-1)", "(-1,1)"};
    string[] intervalList = {"nihil","(-\u221E,-1)", "(-\u221E,1)", "(-\u221E,0)", "(-1, \u221E)", "(0, \u221E)", "(1, \u221E)",
        "(-1,0)", "(0,1)", "(-1,1)"}; //\u221E
    string[] trigonList = {"0", "sin(x)", "cos(x)", "sin(-x)", "cos(-x)", "sin(π-x)", "cos(π-x)", "sin(x)\n+cos(x)", "sin(x)\n-cos(x)", "cos(x)\n-sin(x)", "-sin(x)\n-cos(x)" }; //1D6D1
    float[] sortList = {1f, 2f, 3f, 4f, 5f};

    TextMeshProUGUI costText;
    string numberValueInitial;
    string numberSelectedString;
    string modeNumber = "add";
    float numberSelectedNumerator;
    float numberSelectedDenominator;
    Fraction numberSelectedFraction;

    protected override void Start()
    {
        base.Start();
        costText = GetComponentInChildren<TextMeshProUGUI>();
        if (cardFrameAttached != null && cardFrameAttached.IsInitialized)
            return; // ActivateComponents() already set our values
        numberValueInitial = SetNumber();
    }

    public string SetNumber()
    {
        numberSelected = -1000f;
        numberSelectedString = " ";
        if (activated)
        {
            if(modeNumber == "add")
            {
                float numberRaw = -100f;
                do
                {
                    numberRaw = Mathf.Round(Random.Range(0f, maxValueAdd));
                } while (numberRaw == 0f || numberRaw == -100f);

                float signRandom = Random.Range(0f, 1f);
                float sign = 1f; ;
                if (signRandom > 0.5f)
                {
                    sign = 1f;
                }
                else
                {
                    sign = -1f;
                }

                numberSelected = numberRaw * sign;
                if (cardSuper)
                {
                    numberSelected = 0f;
                }
                numberSelectedString = numberSelected.ToString();

            }
            else if (modeNumber == "multiply") 
            {
                float numberRaw = -100f;
                do
                {
                    numberRaw = Mathf.Round(Random.Range(0f, maxValueMultiply));
                } while (numberRaw == 0f || numberRaw == 1f || numberRaw == -100f);

                float signRandom = Random.Range(0f, 1f);
                if (signRandom > 0.5f)
                {
                    numberSelectedFraction = new Fraction((int)numberRaw, 1);
                    numberSelectedNumerator = numberRaw;
                    numberSelectedDenominator = 1f;
                    numberSelected = numberRaw;
                    numberSelectedString = numberRaw.ToString();
                }
                else
                {
                    numberSelectedFraction = new Fraction(1, (int)numberRaw);
                    numberSelectedNumerator = 1f;
                    numberSelectedDenominator = numberRaw;
                    numberSelected = 1f / numberRaw;
                    numberSelectedString = "1/" + numberRaw.ToString();
                }

                if (cardSuper)
                {
                    numberSelected = 1f;
                }
            }
            else if (modeNumber == "gcd") 
            {
                int randomIndex = Random.Range(0, gcdList.Length);
                numberSelected = gcdList[randomIndex];
                numberSelectedString = numberSelected.ToString();
            }
            else if (modeNumber == "vector")
            {
                int randomIndex;
                do
                {
                    randomIndex = Random.Range(0, vectorList.Length);
                } while (randomIndex == 0);
                numberSelected = (float)randomIndex;
                numberSelectedString = vectorList[randomIndex];
            }
            else if (modeNumber == "interval")
            {
                int randomIndex;
                do
                {
                    randomIndex = Random.Range(0, intervalList.Length);
                } while (randomIndex == 0);
                numberSelected = (float)randomIndex;
                numberSelectedString = intervalList[randomIndex];
                if (costText == null) costText = GetComponentInChildren<TextMeshProUGUI>();
                if (costText != null) costText.fontSize = 16f;
            }
            else if (modeNumber == "trigon")
            {
                int randomIndex;
                do
                {
                    randomIndex = Random.Range(0, trigonList.Length);
                } while (randomIndex == 0);
                numberSelected = (float)randomIndex;
                numberSelectedString = trigonList[randomIndex];
                if (costText == null) costText = GetComponentInChildren<TextMeshProUGUI>();
                if (costText != null) costText.fontSize = 14f;
            }
            else if (modeNumber == "sort")
            {
                int randomIndex = Random.Range(0, sortList.Length);
                numberSelected = sortList[randomIndex];
                numberSelectedString = numberSelected.ToString();
            }
        }

        if (costText == null)
            costText = GetComponentInChildren<TextMeshProUGUI>();
        if (costText != null)
            costText.text = numberSelectedString;

        return numberSelectedString;
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
    }

    public float ComputeMergeNumberGain(float newNumber)
    {
        if(modeNumber == "add")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }

            if (Mathf.Abs(numberSelected) < 0.01f && Mathf.Abs(newNumber) < 0.01f)
            {
                return 3f;
            }
            if (Mathf.Abs(numberSelected) < 0.01f && Mathf.Abs(newNumber) >= 0.01f)
            {
                return -1f;
            }
            if (Mathf.Abs(numberSelected) >= 0.01f && Mathf.Abs(newNumber) < 0.01f)
            {
                return 0f;
            }
            if (Mathf.Abs(numberSelected + newNumber) < 0.01f)
            {
                return 2f;
            }

            float numberMerged = numberSelected + newNumber;
            float absDistToZero = Mathf.Abs(numberMerged);
            // Must match MergeNumberCard's decay formula exactly (see line ~1424).
            // Previously used -3f here which made the preview report one tier
            // better than the real merge (sum=3 showed neutral but delivered 0.9×).
            float normalizedDist = (absDistToZero - 2f) / 10f;
            float manaMult = Mathf.Max(1f - normalizedDist, 0.7f);

            if (manaMult > 1f)
            {
                return 1f;
            }
            else if (manaMult < 1f)
            {
                return -1f;
            }

            return 0f;
        }
        else if (modeNumber == "multiply")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }

            if (Mathf.Abs(numberSelected - 1f) < 0.01f && Mathf.Abs(newNumber - 1f) < 0.01f)
            {
                return 3f;
            }
            if (Mathf.Abs(numberSelected - 1f) < 0.01f && Mathf.Abs(newNumber - 1f) > 0.01f)
            {
                return -1f;
            }
            if (Mathf.Abs(numberSelected - 1f) > 0.01f && Mathf.Abs(newNumber - 1f) < 0.01f)
            {
                return 0f;
            }

            float numberMerged = numberSelected * newNumber;

            Fraction newFraction = RealToFraction(numberMerged, 0.01);
            if (Mathf.Abs(newFraction.N - 1f) < 0.01f && Mathf.Abs(newFraction.D - 1f) < 0.01f)
            {
                return 2f;
            }
            
            float manaMult;
            if (numberMerged >= 1)
            {
                manaMult = Mathf.Max(1.15f * Mathf.Exp(-Mathf.Pow(numberMerged - 1f, 2f) / 8f), 0.7f);
            }
            else
            {
                manaMult = Mathf.Max(1.15f * Mathf.Exp(-Mathf.Pow(1f / numberMerged - 1f, 2f) / 8f), 0.7f);
            }

            if (manaMult >= 1f)
            {
                return 1f;
            }
            else if (manaMult < 1f)
            {
                return -1f;
            }

            return 0f;

        }
        else if (modeNumber == "gcd")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }

            if (numberSelected == 1 && newNumber == 1)
            {
                return 3f;
            }

            if (numberSelected == 1 && newNumber != 1)
            {
                return -1f;
            }

            if (numberSelected != 1 && newNumber == 1)
            {
                return 0f;
            }
            if (GCD(numberSelected, newNumber) == 1f)
            {
                return 2f;
            }
            else
            {
                return -1f;
            }
            
        }
        else if (modeNumber == "vector")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                return 3f;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                return -1f;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                return 0f;
            }

            if (numberSelected == newNumber)
            {
                return 0f;
            }


            if (numberSelected == 1f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                return 0f ;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                return 0f;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                return 2f;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                return 0f;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                return 0f;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                return 0f;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                return 2f;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                return 0f;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                return 0f;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                return 0f;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                return 0f;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 1f)
            {
                return 0f;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                return 0f;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                return 2f;
            }
        }
        else if (modeNumber == "interval")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                return 3f;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                return -1f;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                return 0f;
            }

            if (numberSelected == newNumber)
            {
                return -1f;
            }

            //Logic starts here
            if (numberSelected == 1f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 9f)
            {
                return 2f;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                return 1f;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 2f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 3f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 5f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 9f)
            {
                return 2f;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                return 2f;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                return 2f;
            }
            if (numberSelected == 7f && newNumber == 9f)
            {
                return -1f;
            }
            if (numberSelected == 8f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {

                return 2f;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 9f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 9f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 9f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 9f && newNumber == 8f)
            {
                return -1f;
            }
        }
        else if (modeNumber == "trigon")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                return 3f;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                return -1f;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                return 0f;
            }

            if (numberSelected == newNumber)
            {
                return 0f;
            }

            //Logic starts here
            if (numberSelected == 1f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                return 0f;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                return -1f;
            }
            if (numberSelected == 1f && newNumber == 9f)
            {
                return 0f;
            }
            if (numberSelected == 1f && newNumber == 10f)
            {
                return 0f;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                return 0f;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                return 0f;
            }
            if (numberSelected == 2f && newNumber == 9f)
            {
                return -1f;
            }
            if (numberSelected == 2f && newNumber == 10f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                return 2f;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                return 0f;
            }
            if (numberSelected == 3f && newNumber == 9f)
            {
                return -1f;
            }
            if (numberSelected == 3f && newNumber == 10f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                return 2f;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                return 2f;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 4f && newNumber == 9f)
            {
                return -1f;
            }
            if (numberSelected == 4f && newNumber == 10f)
            {
                return 0f;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                return 2f;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                return -1f;
            }
            if (numberSelected == 5f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 5f && newNumber == 10f)
            {
                return 0f;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                return -1f; 
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                return 2f;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                return -1f;
            }
            if (numberSelected == 6f && newNumber == 9f)
            {
                return 0f;
            }
            if (numberSelected == 6f && newNumber == 10f)
            {
                return -1f;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                return 0f;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 9f)
            {
                return 1f;
            }
            if (numberSelected == 7f && newNumber == 10f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 1f)
            { 
                return 0f;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                return 0f;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {
                return 0f;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 8f && newNumber == 9f)
            {
                return 2f;
            }
            if (numberSelected == 8f && newNumber == 10f)
            {
                return 1f;
            }
            if (numberSelected == 9f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 9f && newNumber == 2f)
            {
                return 0f;
            }
            if (numberSelected == 9f && newNumber == 3f)
            {
                return 0f;
            }
            if (numberSelected == 9f && newNumber == 4f)
            {
                return 0f;
            }
            if (numberSelected == 9f && newNumber == 5f)
            {
                return 1f;
            }
            if (numberSelected == 9f && newNumber == 6f)
            {
                return 1f;
            }
            if (numberSelected == 9f && newNumber == 7f)
            {
                return 1f;
            }
            if (numberSelected == 9f && newNumber == 8f)
            {
                return 2f;
            }
            if (numberSelected == 9f && newNumber == 10f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 1f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 2f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 3f)
            {
                return 0f;
            }
            if (numberSelected == 10f && newNumber == 4f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 5f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 6f)
            {
                return 0f;
            }
            if (numberSelected == 10f && newNumber == 7f)
            {
                return 2f;
            }
            if (numberSelected == 10f && newNumber == 8f)
            {
                return 1f;
            }
            if (numberSelected == 10f && newNumber == 9f)
            {
                return 1f;
            }

        }
        else if (modeNumber == "sort")
        {
            if (newNumber == -1000f)
            {
                return 0f;
            }

            if (numberSelected == -1000f)
            {
                return 0f;
            }

            if (numberSelected == 0f && newNumber == 0f)
            {
                return 3f;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                return -1f;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                return 0f;
            }

            if (numberSelected == newNumber)
            {
                return 0f;
            }

            if (numberSelected < 6f)
            {
                if (newNumber < 6f)
                {
                    if (numberSelected > newNumber)
                    {
                        return 1f;
                    }
                    else
                    {
                        return -1f;
                    }
                }
                else
                {
                    float num1;
                    float num2;
                    num1 = Mathf.Floor(newNumber / 10f);
                    num2 = newNumber - num1 * 10f;
                    if (numberSelected > num2)
                    {
                        return 2f;
                    }
                    else
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                        return -1f;
                    }
                }
            }
            else
            {
                float num1;
                float num2;
                num1 = Mathf.Floor(numberSelected / 10f);
                num2 = numberSelected - num1 * 10f;

                if (newNumber < 6f)
                {
                    if (num1 > newNumber)
                    {
                        return 2f;
                    }
                    else
                    {
                        return -1f;
                    }
                }
                else
                {
                    float num1_;
                    float num2_;
                    num1_ = Mathf.Floor(newNumber / 10f);
                    num2_ = newNumber - num1_ * 10f;
                    if (num1 > num2_)
                    {
                        return 2f;
                    }
                    else
                    {
                        return -1f;
                    }
                }
            }
        }

        return 0f;

    }

    public void MergeNumberCard(float newNumber)
    {
        if(modeNumber == "add")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (Mathf.Abs(numberSelected) < 0.01f && Mathf.Abs(newNumber) < 0.01f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (Mathf.Abs(numberSelected) < 0.01f && Mathf.Abs(newNumber) >= 0.01f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (Mathf.Abs(numberSelected) >= 0.01f && Mathf.Abs(newNumber) < 0.01f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            numberSelected += newNumber;
            SetNumberValueCard(numberSelected);
            if (Mathf.Abs(numberSelected) < 0.01f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
            }
            else
            {
                float absDistToZero = Mathf.Abs(numberSelected);
                float normalizedDist = (absDistToZero - 2f) / 10f; //was -3f 19th July 2021
                float manaMult = Mathf.Max(1f - normalizedDist, 0.7f);
                cardAttached.ChangeCardMana(manaMult);
            }
        }

        else if (modeNumber == "multiply") 
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (Mathf.Abs(numberSelected - 1f) < 0.01f && Mathf.Abs(newNumber - 1f) < 0.01f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (Mathf.Abs(numberSelected - 1f) < 0.01f && Mathf.Abs(newNumber - 1f) > 0.01f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (Mathf.Abs(numberSelected - 1f) > 0.01f && Mathf.Abs(newNumber - 1f) < 0.01f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            numberSelected *= newNumber;
            numberSelectedFraction = RealToFraction(numberSelected, 0.01f);
            SetNumberValueCard(numberSelectedFraction.N, numberSelectedFraction.D);
            if (Mathf.Abs(numberSelectedFraction.N - 1f) < 0.01f && Mathf.Abs(numberSelectedFraction.D - 1f) < 0.01f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
            }
            else
            {
                float manaMult;
                if (numberSelected >= 1)
                {
                    manaMult = Mathf.Max(1.15f * Mathf.Exp(-Mathf.Pow(numberSelected - 1f, 2f) / 8f), 0.7f);
                }
                else
                {
                    manaMult = Mathf.Max(1.15f * Mathf.Exp(-Mathf.Pow(1f/numberSelected - 1f, 2f) / 8f), 0.7f);
                }
                
                cardAttached.ChangeCardMana(manaMult);
            }

        }

        else if (modeNumber == "gcd")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == 1 && newNumber == 1)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (numberSelected == 1 && newNumber != 1)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (numberSelected != 1 && newNumber == 1)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if(GCD(numberSelected, newNumber) == 1f)
            {
                numberSelected = 1f;
                SetNumberValueCard(numberSelected);
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
            }
            else
            {
                numberSelected = GCD(numberSelected, newNumber);
                SetNumberValueCard(numberSelected);
                cardAttached.ChangeCardMana(manaReductionMultiplier);
            }

        }

        //"(0,0)", "(0,1)", "(1,0)", "(1,1)", "(0,-1)", "(-1,0)", "(-1,-1)", "(1,-1)", "(-1,1)"
        else if (modeNumber == "vector")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == newNumber)
            {
                return;
            }


            if (numberSelected == 1f && newNumber == 2f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                numberSelected = 5f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                numberSelected = 2f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                numberSelected = 4f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                numberSelected = 1f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                numberSelected = 3f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                numberSelected = 3f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                numberSelected = 2f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                numberSelected = 5f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                numberSelected = 1f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                numberSelected = 4f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                numberSelected = 4f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                numberSelected = 6f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                numberSelected = 6f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                numberSelected = 4f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                numberSelected = 4f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                numberSelected = 4f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            //{ "(0,0)", "(0,1)", "(1,0)", "(1,1)", "(0,-1)", "(-1,0)", "(-1,-1)", "(1,-1)", "(-1,1)"};
            if (numberSelected == 8f && newNumber == 1f)
            {
                numberSelected = 8f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                numberSelected = 8f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
        }

        else if (modeNumber == "interval")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == newNumber)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            //Logic starts here
            if (numberSelected == 1f && newNumber == 2f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 9f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 9f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 9f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 9f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                numberSelected = 5f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 9f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 9f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 9f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 9f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 2f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 3f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 4f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 5f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
        }

        else if (modeNumber == "trigon")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 0f && newNumber == 0f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == newNumber)
            {
                return;
            }

            //Logic starts here
            if (numberSelected == 1f && newNumber == 2f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 4f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 5f)
            {
                numberSelected = 1f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 6f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 9f)
            {
                numberSelected = 2f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 1f && newNumber == 10f)
            {
                numberSelected = 6f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 1f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 3f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 4f)
            {
                numberSelected = 2f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 5f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 8f)
            {
                numberSelected = 1f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 9f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 2f && newNumber == 10f)
            {
                numberSelected = 3f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 1f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 2f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 4f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 5f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 6f)
            {
                numberSelected = 10f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 7f)
            {
                numberSelected = 2f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 8f)
            {
                numberSelected =6f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 9f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 3f && newNumber == 10f)
            {
                numberSelected = 10f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 1f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 2f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 3f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 5f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 6f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 8f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 9f)
            {
                numberSelected = 9f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 4f && newNumber == 10f)
            {
                numberSelected = 3f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 1f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 2f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 3f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 4f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 6f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 7f)
            {
                numberSelected = 7f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 8f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 9f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 5f && newNumber == 10f)
            {
                numberSelected = 6f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 1f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 2f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 3f)
            {
                numberSelected = 10f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 4f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 5f)
            {
                numberSelected = 8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 7f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 8f)
            {
                numberSelected =8f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 9f)
            {
                numberSelected = 3f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 6f && newNumber == 10f)
            {
                numberSelected = 10f;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 1f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 2f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 3f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 4f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 5f)
            {
                numberSelected = 7f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 6f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 8f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 9f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 7f && newNumber == 10f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 1f)
            {
                numberSelected = 8f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 2f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 3f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 4f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 5f)
            {
                numberSelected = 8f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 6f)
            {
                numberSelected = 8f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 7f)
            {
                numberSelected = 1f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 9f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 8f && newNumber == 10f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 1f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 2f)
            {
                numberSelected = 9f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 3f)
            {
                numberSelected = 9f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 4f)
            {
                numberSelected = 9f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 5f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 6f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 7f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 8f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 9f && newNumber == 10f)
            {
                numberSelected = 2f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 1f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 2f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 3f)
            {
                numberSelected = 10f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 4f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 5f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 6f)
            {
                numberSelected = 10f;
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 7f)
            {
                numberSelected = 0f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 8f)
            {
                numberSelected = 6f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }
            if (numberSelected == 10f && newNumber == 9f)
            {
                numberSelected = 3f;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                SetNumberValueCard(numberSelected);
                return;
            }


        }

        else if (modeNumber == "sort")
        {
            if (newNumber == -1000f)
            {
                return;
            }

            if (numberSelected == -1000f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == 0f && newNumber == 0f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (numberSelected == 0f && newNumber != 0f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (numberSelected != 0f && newNumber == 0f)
            {
                numberSelected = newNumber;
                SetNumberValueCard(numberSelected);
                return;
            }

            if (numberSelected == newNumber)
            {
                return;
            }

            if (numberSelected < 6f)
            {
                if (newNumber < 6f)
                {
                    if (numberSelected > newNumber)
                    {
                        numberSelected = newNumber * 10f + numberSelected;
                        cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                        SetNumberValueCard(numberSelected);
                    }
                    else
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                    }
                }
                else
                {
                    float num1;
                    float num2;
                    num1 = Mathf.Floor(newNumber / 10f);
                    num2 = newNumber - num1 * 10f;
                    if(numberSelected > num2)
                    {
                        numberSelected = 0f;
                        cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                        SetNumberValueCard(numberSelected);
                    }
                    else
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                    }
                }
            }
            else
            {
                float num1;
                float num2;
                num1 = Mathf.Floor(numberSelected / 10f);
                num2 = numberSelected - num1 * 10f;

                if (newNumber < 6f)
                {
                    if (num1 > newNumber)
                    {
                        numberSelected = 0f;
                        cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                        SetNumberValueCard(numberSelected);
                    }
                    else
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                    }
                }
                else
                {
                    float num1_;
                    float num2_;
                    num1_ = Mathf.Floor(newNumber / 10f);
                    num2_ = newNumber - num1_ * 10f;
                    if (num1 > num2_)
                    {
                        numberSelected = 0f;
                        cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                        SetNumberValueCard(numberSelected);
                    }
                    else
                    {
                        cardAttached.ChangeCardMana(manaReductionMultiplier);
                    }
                }
            }

        }
    }

    public void SetNumberValueCard(float value, float denom=1)
    {
        if(modeNumber == "add")
        {
            costText.text = value.ToString();
        }
        else if (modeNumber == "multiply")
        {
            if(value < 1 && denom ==1)
            {
                float valueNorm = Mathf.Round(1f / value);
                costText.text ="1/" + valueNorm.ToString();
            }
            else if(value >= 1 && denom == 1)
            {
                costText.text = value.ToString();
            }
            else
            {
                costText.text = value.ToString() + "/" + denom.ToString();
            }
        }
        else if (modeNumber == "gcd")
        {
            costText.text = value.ToString();
        }
        else if (modeNumber == "vector")
        {
            costText.text = vectorList[(int)value];
        }
        else if (modeNumber == "interval")
        {
            costText.text = intervalList[(int)value];
        }
        else if (modeNumber == "trigon")
        {
            costText.text = trigonList[(int)value];
        }
        else if (modeNumber == "sort")
        {
            if (value < 6f)
            {
                costText.text = value.ToString();
            }
            else
            {
                float num1;
                float num2;
                num1 = Mathf.Floor(value / 10f);
                num2 = value - num1 * 10f;
                costText.text = num1.ToString() + "; " + num2.ToString();
            }
        }

    }

    public void SetModeNumber(string modeNumberSet)
    {
        modeNumber = modeNumberSet;
    }

    public string GetModeNumber()
    {
        return modeNumber;
    }

    public Fraction RealToFraction(double value, double accuracy)
    {
        if (accuracy <= 0.0 || accuracy >= 1.0)
        {
            throw new System.ArgumentOutOfRangeException("accuracy", "Must be > 0 and < 1.");
        }

        int sign = System.Math.Sign(value);

        if (sign == -1)
        {
            value = System.Math.Abs(value);
        }

        // Accuracy is the maximum relative error; convert to absolute maxError
        double maxError = sign == 0 ? accuracy : value * accuracy;

        int n = (int)System.Math.Floor(value);
        value -= n;

        if (value < maxError)
        {
            return new Fraction(sign * n, 1);
        }

        if (1 - maxError < value)
        {
            return new Fraction(sign * (n + 1), 1);
        }

        // The lower fraction is 0/1
        int lower_n = 0;
        int lower_d = 1;

        // The upper fraction is 1/1
        int upper_n = 1;
        int upper_d = 1;

        while (true)
        {
            // The middle fraction is (lower_n + upper_n) / (lower_d + upper_d)
            int middle_n = lower_n + upper_n;
            int middle_d = lower_d + upper_d;

            if (middle_d * (value + maxError) < middle_n)
            {
                // real + error < middle : middle is our new upper
                upper_n = middle_n;
                upper_d = middle_d;
            }
            else if (middle_n < (value - maxError) * middle_d)
            {
                // middle < real - error : middle is our new lower
                lower_n = middle_n;
                lower_d = middle_d;
            }
            else
            {
                // Middle is our best fraction
                return new Fraction((n * middle_d + middle_n) * sign, middle_d);
            }
        }
    }

    public struct Fraction
    {
        public Fraction(int n, int d)
        {
            N = n;
            D = d;
        }

        public int N { get; private set; }
        public int D { get; private set; }
    }

    public static float GCD(float p, float q)
    {
        if (q == 0f)
        {
            return p;
        }

        int r = ((int) p) % ((int) q);
        float r_ = (float)r;
        return GCD(q, r_);
    }

}
