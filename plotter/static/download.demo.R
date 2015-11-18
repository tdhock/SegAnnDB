chromfactor <- function(x)factor(x,c(1:22,"X"))
getCSV <- function
### Download a csv export file from SegAnnDB.
(name,
### SegAnnDB profile name of data to download. You can get a list of
### current names by looking on the website or this CSV file:
### http://bioviz.rocq.inria.fr/csv_profiles/
 data.type="copies",
### character specifying data type to download e.g. "copies",
### "regions", "breaks".
 base="http://bioviz.rocq.inria.fr/",
### Base URL of SegAnnDB.
 user="None"
### SegAnnDB username of annotations or model to download, defaults to
### None which is the anonymous user.
 ){
  for(ch in list(name,data.type,base,user)){
    stopifnot(is.character(ch))
    stopifnot(length(ch)==1)
  }
  u <- sprintf("%s/export/%s/%s/%s/csv/",base,user,name,data.type)
  f <- url(u)
  df <- read.csv(f)
  if("chromosome"%in%names(df)){
    df$chromosome <- chromfactor(df$chromosome)
  }
  df
### data.frame of downloaded info.
}

## First download the table of profiles, so you can see what profiles
## are available.
info <- read.csv(url("http://bioviz.rocq.inria.fr/csv_profiles/"))

tables <- list(copies=data.frame(),
               breaks=data.frame())               
n.profiles <- 2 # only download the first few profiles.
for(i in 1:n.profiles){ 
  name <- as.character(info$name[i])
  cat(sprintf("downloading for profile %4d / %4d %s\n",i,n.profiles,name))
  for(data.type in names(tables)){
    thisTable <- getCSV(name, data.type)
    thisTable$profile_name <- info$name[i]
    tables[[data.type]] <- rbind(tables[[data.type]],thisTable)
  }
}

library(ggplot2)
library(grid)
loss.gain.colors <-  c("amplification"="#d02a2a",
                       "gain"="#ff7d7d",
                       "normal"='#f6f4bf',
                       "loss"="#93b9ff",
                       "deletion"="#3564ba",
                       "unlabeled"="#0adb0a",
                       "multilabeled"="black")
tables$copies$annotation <-
  factor(tables$copies$annotation,names(loss.gain.colors))
p <- ggplot()+
  geom_segment(aes(min/1e6,logratio,
                   xend=max/1e6,yend=logratio,
                   colour=annotation),
               data=tables$copies,lwd=2)+
  geom_vline(aes(xintercept=position/1e6),
             data=tables$breaks,
             linetype="dashed")+
  scale_colour_manual(values=loss.gain.colors)+
  facet_grid(profile_name~chromosome,scales="free",space="free_x")+
  theme_bw()+
  scale_x_continuous("position in mega base pairs",breaks=c(100,200))+
  theme(panel.margin=unit(0,"lines"))
print(p)
