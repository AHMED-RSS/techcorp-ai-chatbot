"""
Vision Agent
"""



from services.vision_service import (

    analyze_image,

    analyze_chart,

    analyze_document_image

)





def run_vision_agent(

        image_path,

        request

):


    request_lower = request.lower()





    if "chart" in request_lower:

        return analyze_chart(

            image_path

        )





    elif (

        "document" in request_lower

        or

        "text" in request_lower

    ):


        return analyze_document_image(

            image_path

        )





    else:


        return analyze_image(

            image_path,

            request

        )