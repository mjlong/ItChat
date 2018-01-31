#!/bin/bash
files=(./*)
filesProtected=(rmduplicate.sh )

echo ${files[@]}
echo ${#files[@]}
for f in "${files[@]}"
do 
  filesp=(./*)
  if echo ${filesp[@]} | grep -w "$f"  > /dev/null; # $f still in list
  then 
      echo "processing file $f ..."


      for fp in "${filesp[@]}"
      do 
        if [ "$f" != "$fp" ]
        then 
          DIFF=$(diff "$f" "$fp");
          if [ "$DIFF" == "" ] 
          then 
            echo "....$f and $fp are duplicated because DIFF=$DIFF"
            rm "$fp"
            echo "....$fp removed"
          fi  
        fi 
      done

      filesize=$(stat --printf=%s "$f")
      if [ "0" -eq "$filesize" ]
      then 
         echo $f is empty because the size is $filesize
         rm "$f"
         echo "....$f removed"
      fi
  fi
  sleep 1
done

#for var in "$@"
#do 
#    if echo ${files[@]} | grep -w ./$var  > /dev/null;
#    then 
#        echo $var exists
#        if echo ${filesProtected[@]} | grep -w $var  > /dev/null;       
#        then 
#            echo $var is protected
#        fi
#    else
#        echo $var does not exist
#    fi
#done
