"""
Vision Service
Handles multimodal image understanding
"""

from pathlib import Path
from core.providers import AIProvider


# Installed Ollama vision model
VISION_MODEL = "llama3.2-vision:latest"



def check_vision_model(
    ai_provider: AIProvider | None = None,
):

    try:

        if ai_provider is None:
            return False

        models = ai_provider.list_models()


        available = []


        # New Ollama format

        if hasattr(models, "models"):

            for model in models.models:

                available.append(
                    model.model
                    if hasattr(model, "model")
                    else str(model)
                )


        # Dictionary fallback

        elif isinstance(models, dict):

            available = [

                m.get("name")

                for m in models.get(
                    "models",
                    []
                )

            ]



        return VISION_MODEL in available



    except Exception:


        return False







def analyze_image(

        image_path,

        question="Analyze this image",

        ai_provider: AIProvider | None = None,

):


    image_path = Path(

        image_path

    )



    if not image_path.exists():


        return (

            f"Image not found: {image_path}"

        )




    try:


        if ai_provider is None:
            return "Vision provider is not configured."

        response = ai_provider.chat(

            model=VISION_MODEL,


            messages=[

                {

                    "role": "user",


                    "content": question,


                    "images": [

                        str(image_path)

                    ]

                }

            ]

        )



        return response["message"]["content"]




    except Exception as e:


        return f"""

❌ Vision Model Error:


{str(e)}


Check that Ollama has:


AI provider model list


You should see:


{VISION_MODEL}


"""









def analyze_chart(image_path):


    prompt = """

You are a professional chart analyst.


Analyze this chart image.


Return:


## Chart Type

Identify the chart type.


## Title

Find the chart title.


## Axes

Explain:

- X-axis

- Y-axis


## Data

Extract important values.


## Trends

Explain increases, decreases, patterns.


## Conclusion

Give the main insight.


If information is unclear, say so.


"""



    return analyze_image(

        image_path,

        prompt

    )









def analyze_document_image(image_path):


    prompt = """

You are a document analysis AI.


Analyze this image.


Extract:


1. All visible text

2. Headings

3. Tables

4. Important information

5. Summary


Keep the structure clear.


"""



    return analyze_image(

        image_path,

        prompt

    )









def compare_images(

        image1,

        image2,

        ai_provider: AIProvider | None = None,

):


    image1 = Path(image1)

    image2 = Path(image2)



    if not image1.exists():

        return f"Missing image: {image1}"


    if not image2.exists():

        return f"Missing image: {image2}"




    try:


        if ai_provider is None:
            return "Vision provider is not configured."

        response = ai_provider.chat(


            model=VISION_MODEL,


            messages=[


                {


                    "role": "user",


                    "content": """

Compare these two images.



Explain:


- Similarities

- Differences

- Changes

- Important observations



""",


                    "images": [

                        str(image1),

                        str(image2)

                    ]

                }

            ]

        )



        return response["message"]["content"]





    except Exception as e:


        return str(e)









def describe_image(image_path):


    prompt = """

Describe this image in detail.


Include:


- Objects

- People

- Text

- Environment

- Important details



"""



    return analyze_image(

        image_path,

        prompt

    )
